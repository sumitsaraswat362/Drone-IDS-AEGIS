"""
AEGIS Drone IDS — Anomaly Detector
Uses an Isolation Forest trained on normal MAVLink telemetry to detect
novel/unknown attack patterns beyond what rule-based detection covers.
"""
import numpy as np
from collections import deque
from typing import Optional, List
from sklearn.ensemble import IsolationForest
from ..simulator.mavlink_simulator import MAVLinkPacket, MSG_GPS_RAW_INT, MSG_ATTITUDE


class FeatureExtractor:
    """
    Extracts a fixed-length numerical feature vector from a sliding window
    of MAVLink packets for the Isolation Forest model.

    Feature vector (12 dimensions):
    [0]  lat_delta_m         — position change since last GPS packet
    [1]  lon_delta_m         — longitude change
    [2]  alt_delta_m         — altitude change
    [3]  hdop                — GPS dilution of precision
    [4]  roll_rate           — roll angular rate
    [5]  pitch_rate          — pitch angular rate
    [6]  yaw_rate            — yaw angular rate
    [7]  gps_hz             — GPS packet rate in last 1 second
    [8]  hb_hz              — heartbeat rate in last 1 second
    [9]  unique_sysids       — count of unique system IDs seen recently
    [10] max_cmd_count       — command packets in last 5 seconds
    [11] timestamp_monotonic — 1 if ts is monotonically increasing, 0 if stale
    """

    FEATURE_DIM = 12

    def __init__(self, window_s: float = 2.0):
        self.window_s   = window_s
        self._gps_win   : deque = deque()
        self._hb_win    : deque = deque()
        self._cmd_win   : deque = deque()
        self._sysids    : deque = deque()
        self._last_lat  : Optional[float] = None
        self._last_lon  : Optional[float] = None
        self._last_alt  : Optional[float] = None
        self._last_roll : float = 0.0
        self._last_pitch: float = 0.0
        self._last_yaw  : float = 0.0
        self._last_ts   : float = 0.0
        self._max_ts    : float = 0.0

    def _purge(self, q: deque, t: float, window: float):
        while q and q[0] < t - window:
            q.popleft()

    def extract(self, pkt: MAVLinkPacket) -> Optional[np.ndarray]:
        t  = pkt.timestamp_s
        mid = pkt.msg_id

        # Track system IDs
        self._sysids.append((t, pkt.system_id))
        while self._sysids and self._sysids[0][0] < t - self.window_s:
            self._sysids.popleft()

        # Update max timestamp for monotonicity check
        if t > self._max_ts:
            self._max_ts = t
        ts_monotonic = 1.0 if t >= self._max_ts - 0.01 else 0.0

        # GPS features
        lat_delta = lon_delta = alt_delta = hdop = 0.0
        if mid == MSG_GPS_RAW_INT:
            lat_m  = pkt.payload.get('lat', 0) / 1e7 * 111_000
            lon_m  = pkt.payload.get('lon', 0) / 1e7 * 111_000
            alt_m  = pkt.payload.get('alt', 0) / 1000.0
            hdop   = pkt.payload.get('eph', 120) / 100.0

            if self._last_lat is not None:
                lat_delta = lat_m - self._last_lat
                lon_delta = lon_m - self._last_lon
                alt_delta = alt_m - self._last_alt

            self._last_lat = lat_m
            self._last_lon = lon_m
            self._last_alt = alt_m

            self._gps_win.append(t)
            self._purge(self._gps_win, t, 1.0)
        else:
            hdop = 1.2   # default when no GPS packet

        # Attitude features
        roll_rate = pitch_rate = yaw_rate = 0.0
        if mid == MSG_ATTITUDE:
            roll_rate  = abs(pkt.payload.get('rollspeed', 0))
            pitch_rate = abs(pkt.payload.get('pitchspeed', 0))
            yaw_rate   = abs(pkt.payload.get('yawspeed', 0))

        # Heartbeat rate
        if mid == 0:  # HEARTBEAT
            self._hb_win.append(t)
            self._purge(self._hb_win, t, 1.0)

        # Command count
        if mid == 76:  # COMMAND_LONG
            self._cmd_win.append(t)
            self._purge(self._cmd_win, t, 5.0)

        gps_hz  = float(len(self._gps_win))
        hb_hz   = float(len(self._hb_win))
        cmd_cnt = float(len(self._cmd_win))
        n_sysids = float(len(set(s for _, s in self._sysids)))

        return np.array([
            lat_delta, lon_delta, alt_delta, hdop,
            roll_rate, pitch_rate, yaw_rate,
            gps_hz, hb_hz, n_sysids, cmd_cnt, ts_monotonic,
        ], dtype=np.float32)


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector.
    Train on normal traffic, then score live packets.
    """

    def __init__(self, contamination: float = 0.01, n_estimators: int = 100,
                 random_state: int = 42, score_threshold: float = -0.5):
        self.model = IsolationForest(
            contamination  = contamination,
            n_estimators   = n_estimators,
            random_state   = random_state,
            n_jobs         = -1,
        )
        self.extractor       = FeatureExtractor()
        self.score_threshold = score_threshold  # below this → anomaly
        self._is_trained     = False
        self._training_X     : List[np.ndarray] = []

    def feed_normal(self, packets: List[MAVLinkPacket]) -> None:
        """Feed a batch of known-clean packets to build the training set."""
        for pkt in packets:
            feat = self.extractor.extract(pkt)
            if feat is not None:
                self._training_X.append(feat)

    def train(self) -> None:
        """Fit the Isolation Forest on accumulated normal traffic."""
        if len(self._training_X) < 10:
            raise ValueError("Need at least 10 normal packets to train.")
        X = np.vstack(self._training_X)
        self.model.fit(X)
        self._is_trained = True
        # Reset extractor state for live scoring
        self.extractor = FeatureExtractor()

    def score_packet(self, pkt: MAVLinkPacket) -> Optional[dict]:
        """
        Score a live packet. Returns an alert dict if anomalous, else None.
        Score < -0.1 indicates anomaly (Isolation Forest convention: more negative = more anomalous).
        """
        if not self._is_trained:
            return None
        feat = self.extractor.extract(pkt)
        if feat is None:
            return None

        score = float(self.model.score_samples(feat.reshape(1, -1))[0])
        if score < self.score_threshold:
            severity = 'CRITICAL' if score < -0.3 else 'HIGH' if score < -0.2 else 'MEDIUM'
            return {
                'rule':        'ML_ANOMALY_DETECTION',
                'severity':    severity,
                'timestamp_s': pkt.timestamp_s,
                'msg_id':      pkt.msg_id,
                'system_id':   pkt.system_id,
                'detail':      f"Isolation Forest anomaly score={score:.4f} (threshold={self.score_threshold})",
                'sha256':      pkt.sha256(),
                'ml_score':    score,
            }
        return None
