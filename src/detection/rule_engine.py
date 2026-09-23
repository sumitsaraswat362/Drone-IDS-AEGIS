"""
AEGIS Drone IDS — Rule-Based Detection Engine
Detects known attack signatures using deterministic rules derived from
MAVLink protocol invariants and UAV flight envelope constraints.
"""
import math
from collections import deque
from typing import Optional
from ..simulator.mavlink_simulator import (
    MAVLinkPacket, MSG_HEARTBEAT, MSG_GPS_RAW_INT,
    MSG_COMMAND_LONG, MSG_GLOBAL_POSITION_INT,
    NORMAL_GPS_HDOP_MAX, NORMAL_ALT_MAX_M, NORMAL_SPEED_MAX_MPS,
)

# Detection thresholds
GPS_JUMP_THRESHOLD_M       = 50.0   # Max legitimate position jump in 0.2s
GPS_HDOP_SPOOF_THRESHOLD   = 0.5    # Abnormally low HDOP → spoofed signal
GPS_ALT_MAX_M              = 150.0  # Hard ceiling (above DGCA limit)
DOS_HEARTBEAT_WINDOW_S     = 1.0    # Time window to count heartbeats
DOS_HEARTBEAT_MAX_PER_S    = 10     # Normal max heartbeats per second
REPLAY_TIMESTAMP_DELTA_S   = 2.0    # Stale packet threshold (seconds)
CMD_UNKNOWN_SYSID_THRESHOLD = 10    # System IDs above this from GCS are suspicious


def _haversine_m(lat1_e7: int, lon1_e7: int, lat2_e7: int, lon2_e7: int) -> float:
    """Returns distance in metres between two positions given as 1e7 degree integers."""
    R = 6_371_000.0
    lat1 = math.radians(lat1_e7 / 1e7)
    lat2 = math.radians(lat2_e7 / 1e7)
    dlat = lat2 - lat1
    dlon = math.radians((lon2_e7 - lon1_e7) / 1e7)
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


class RuleEngine:
    """
    Stateful rule-based IDS that processes one MAVLink packet at a time
    and returns an alert dict if a rule fires, or None for clean packets.

    Rules implemented:
    R1 — GPS Position Jump (GPS Spoofing indicator)
    R2 — GPS HDOP Anomaly (abnormally clean signal → spoofed)
    R3 — GPS Altitude Ceiling Violation
    R4 — Heartbeat Flood (Denial-of-Service indicator)
    R5 — Unknown Source System ID (Command Injection indicator)
    R6 — Stale Replay Timestamp (Replay Attack indicator)
    R7 — Disarm/Land Command from non-GCS sender
    """

    def __init__(self, gcs_system_id: int = 255):
        self.gcs_id         = gcs_system_id
        self._last_lat      : Optional[int]   = None
        self._last_lon      : Optional[int]   = None
        self._last_ts       : Optional[float] = None
        self._hb_times      : deque           = deque()
        self._known_sys_ids : set             = {1, gcs_system_id}
        self._max_seen_ts   : float           = 0.0

    def _make_alert(self, pkt: MAVLinkPacket, rule: str,
                    severity: str, detail: str) -> dict:
        return {
            'rule':        rule,
            'severity':    severity,
            'timestamp_s': pkt.timestamp_s,
            'msg_id':      pkt.msg_id,
            'system_id':   pkt.system_id,
            'detail':      detail,
            'sha256':      pkt.sha256(),
        }

    def process(self, pkt: MAVLinkPacket) -> Optional[dict]:
        """Process one packet and return an alert dict or None."""
        alert = None
        t = pkt.timestamp_s

        # Track max observed timestamp for replay detection
        if t > self._max_seen_ts:
            self._max_seen_ts = t

        # ── R4: Heartbeat Flood (DoS) ────────────────────────────────────────
        if pkt.msg_id == MSG_HEARTBEAT:
            self._hb_times.append(t)
            # Purge old entries
            while self._hb_times and self._hb_times[0] < t - DOS_HEARTBEAT_WINDOW_S:
                self._hb_times.popleft()
            if len(self._hb_times) > DOS_HEARTBEAT_MAX_PER_S:
                alert = self._make_alert(pkt, 'R4_HEARTBEAT_FLOOD', 'HIGH',
                    f"{len(self._hb_times)} heartbeats in {DOS_HEARTBEAT_WINDOW_S}s "
                    f"(threshold: {DOS_HEARTBEAT_MAX_PER_S})")

        # ── R5: Unknown Source System ID ─────────────────────────────────────
        if pkt.system_id not in self._known_sys_ids:
            if pkt.msg_id == MSG_COMMAND_LONG:
                alert = self._make_alert(pkt, 'R5_UNKNOWN_SRC_COMMAND', 'CRITICAL',
                    f"COMMAND_LONG from unknown system_id={pkt.system_id}")
            elif pkt.msg_id == MSG_HEARTBEAT:
                # New system IDs seen in heartbeats are noted (not necessarily malicious)
                self._known_sys_ids.add(pkt.system_id)

        # ── R7: Disarm/Land/RTL from non-GCS sender ──────────────────────────
        if pkt.msg_id == MSG_COMMAND_LONG and pkt.system_id != self.gcs_id:
            cmd = pkt.payload.get('command', -1)
            if cmd in (21, 20, 400):   # LAND, RTL, DISARM
                cmd_name = {21: 'LAND', 20: 'RTL', 400: 'DISARM'}.get(cmd, str(cmd))
                alert = self._make_alert(pkt, 'R7_FORGED_COMMAND', 'CRITICAL',
                    f"Command {cmd_name} (id={cmd}) from non-GCS sender (sys_id={pkt.system_id})")

        # ── GPS-based rules ───────────────────────────────────────────────────
        if pkt.msg_id == MSG_GPS_RAW_INT:
            lat = pkt.payload.get('lat', 0)
            lon = pkt.payload.get('lon', 0)
            alt_m = pkt.payload.get('alt', 0) / 1000.0
            hdop  = pkt.payload.get('eph', 120) / 100.0

            # R1: Position jump
            if self._last_lat is not None and self._last_ts is not None:
                dt = max(t - self._last_ts, 1e-6)
                dist_m = _haversine_m(self._last_lat, self._last_lon, lat, lon)
                implied_speed = dist_m / dt
                if dist_m > GPS_JUMP_THRESHOLD_M and implied_speed > NORMAL_SPEED_MAX_MPS * 3:
                    alert = self._make_alert(pkt, 'R1_GPS_POSITION_JUMP', 'CRITICAL',
                        f"Position jumped {dist_m:.1f}m in {dt:.2f}s "
                        f"(implied speed {implied_speed:.1f} m/s)")

            # R2: Abnormally low HDOP (spoofed GPS signal is too perfect)
            if hdop < GPS_HDOP_SPOOF_THRESHOLD:
                alert = self._make_alert(pkt, 'R2_GPS_HDOP_ANOMALY', 'HIGH',
                    f"HDOP={hdop:.2f} is abnormally low (threshold={GPS_HDOP_SPOOF_THRESHOLD}) "
                    "— possible GPS simulator/spoofer")

            # R3: Altitude ceiling
            if alt_m > GPS_ALT_MAX_M:
                alert = self._make_alert(pkt, 'R3_ALT_CEILING_VIOLATION', 'MEDIUM',
                    f"Altitude {alt_m:.1f}m exceeds ceiling {GPS_ALT_MAX_M}m")

            self._last_lat = lat
            self._last_lon = lon
            self._last_ts  = t

        # ── R6: Replay (stale timestamp) ─────────────────────────────────────
        if t < self._max_seen_ts - REPLAY_TIMESTAMP_DELTA_S:
            if not alert:   # Don't override a higher-priority alert
                alert = self._make_alert(pkt, 'R6_REPLAY_ATTACK', 'HIGH',
                    f"Packet timestamp {t:.3f}s is {self._max_seen_ts - t:.2f}s "
                    "behind current stream (stale replay)")

        return alert
