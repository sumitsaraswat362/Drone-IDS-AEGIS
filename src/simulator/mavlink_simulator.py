"""
AEGIS Drone IDS — MAVLink Traffic Simulator
Generates realistic MAVLink v2 packet streams for a simulated UAV mission.
Used to produce a baseline of normal traffic for the IDS training and testing.
"""
import time
import math
import random
import struct
import hashlib
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── MAVLink Message IDs (subset used in simulation) ─────────────────────────
MSG_HEARTBEAT           = 0
MSG_GPS_RAW_INT         = 24
MSG_ATTITUDE            = 30
MSG_GLOBAL_POSITION_INT = 33
MSG_RC_CHANNELS_RAW     = 35
MSG_COMMAND_LONG        = 76
MSG_PARAM_SET           = 23
MSG_STATUSTEXT          = 253

# ── Normal flight envelope constants ─────────────────────────────────────────
NORMAL_GPS_HDOP_MAX   = 2.0          # Horizontal dilution of precision
NORMAL_ALT_MAX_M      = 120.0        # Max altitude (DGCA limit)
NORMAL_SPEED_MAX_MPS  = 15.0         # Max speed m/s
NORMAL_HEARTBEAT_HZ   = 1.0          # Heartbeats per second
NORMAL_ATTITUDE_HZ    = 10.0         # Attitude updates per second


@dataclass
class MAVLinkPacket:
    """Represents a single MAVLink v2 packet."""
    timestamp_s:    float
    msg_id:         int
    system_id:      int
    component_id:   int
    sequence:       int
    payload:        dict
    is_attack:      bool  = False
    attack_type:    Optional[str] = None

    def sha256(self) -> str:
        """Cryptographic hash for chain-of-custody logging."""
        raw = f"{self.timestamp_s}:{self.msg_id}:{self.system_id}:{self.sequence}:{self.payload}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        d = asdict(self)
        d['sha256'] = self.sha256()
        return d


class UAVPhysicsModel:
    """Simple 3-DOF UAV physics model for generating realistic telemetry."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        # Initial position: IIT Bombay campus (lat/lon in 1e7 degrees)
        self.lat   = int(19.1334 * 1e7)
        self.lon   = int(72.9133 * 1e7)
        self.alt_m = 50.0              # altitude above takeoff in metres
        self.vx    = 2.0               # m/s east
        self.vy    = 1.5               # m/s north
        self.vz    = 0.0               # m/s down (positive = descending)
        self.roll  = 0.02              # rad
        self.pitch = -0.03             # rad
        self.yaw   = 0.785             # 45° heading
        self.hdop  = 1.2
        self.satellites_visible = 12
        self._t    = 0.0

    def step(self, dt: float = 0.1) -> dict:
        """Advance simulation by dt seconds and return telemetry snapshot."""
        self._t += dt

        # Gentle sinusoidal flight path
        self.vx = 3.0 * math.sin(self._t * 0.1) + self.np_rng.normal(0, 0.05)
        self.vy = 3.0 * math.cos(self._t * 0.1) + self.np_rng.normal(0, 0.05)
        self.alt_m = 50.0 + 10.0 * math.sin(self._t * 0.05) + self.np_rng.normal(0, 0.2)

        # Convert velocity to lat/lon delta (rough 1 deg ≈ 111km)
        self.lat += int(self.vy * dt / 111000 * 1e7)
        self.lon += int(self.vx * dt / (111000 * math.cos(math.radians(19.13))) * 1e7)

        self.roll  = 0.1 * math.sin(self._t * 0.3) + self.np_rng.normal(0, 0.005)
        self.pitch = 0.05 * math.cos(self._t * 0.2) + self.np_rng.normal(0, 0.005)
        self.yaw  += 0.001 + self.np_rng.normal(0, 0.001)
        self.hdop  = 1.2 + 0.3 * abs(math.sin(self._t * 0.02)) + self.np_rng.normal(0, 0.05)

        return {
            'lat': self.lat,
            'lon': self.lon,
            'alt_mm': int(self.alt_m * 1000),
            'vx': round(self.vx, 3),
            'vy': round(self.vy, 3),
            'vz': round(self.vz, 3),
            'hdop': round(max(0.5, self.hdop), 3),
            'satellites_visible': self.satellites_visible,
            'roll': round(self.roll, 4),
            'pitch': round(self.pitch, 4),
            'yaw': round(self.yaw % (2 * math.pi), 4),
        }


class MAVLinkSimulator:
    """
    Generates a stream of realistic MAVLink v2 packets for a UAV mission.

    Usage:
        sim = MAVLinkSimulator(duration_s=120, seed=42)
        for packet in sim.stream():
            process(packet)
    """

    def __init__(self, duration_s: float = 120.0, seed: int = 42,
                 system_id: int = 1, gcs_id: int = 255):
        self.duration_s  = duration_s
        self.seed        = seed
        self.system_id   = system_id
        self.gcs_id      = gcs_id
        self.physics     = UAVPhysicsModel(seed=seed)
        self.rng         = random.Random(seed)
        self._seq        = 0
        self._t          = 0.0
        self._dt         = 0.1          # 10 Hz simulation tick

    def _next_seq(self) -> int:
        s = self._seq
        self._seq = (self._seq + 1) % 256
        return s

    def _make_packet(self, msg_id: int, payload: dict,
                     sender_id: Optional[int] = None) -> MAVLinkPacket:
        return MAVLinkPacket(
            timestamp_s  = round(self._t, 3),
            msg_id       = msg_id,
            system_id    = sender_id if sender_id else self.system_id,
            component_id = 1,
            sequence     = self._next_seq(),
            payload      = payload,
        )

    def stream(self):
        """Yield MAVLink packets at realistic rates for the mission duration."""
        _hb_interval   = 1.0 / NORMAL_HEARTBEAT_HZ
        _att_interval  = 1.0 / NORMAL_ATTITUDE_HZ
        _last_hb       = -_hb_interval
        _last_att      = -_att_interval

        while self._t <= self.duration_s:
            telem = self.physics.step(self._dt)

            # GPS (5 Hz)
            if int(self._t * 5) != int((self._t - self._dt) * 5):
                yield self._make_packet(MSG_GPS_RAW_INT, {
                    'lat':                 telem['lat'],
                    'lon':                 telem['lon'],
                    'alt':                 telem['alt_mm'],
                    'eph':                 int(telem['hdop'] * 100),
                    'satellites_visible':  telem['satellites_visible'],
                    'fix_type':            3,
                })

            # Global position (4 Hz)
            if int(self._t * 4) != int((self._t - self._dt) * 4):
                yield self._make_packet(MSG_GLOBAL_POSITION_INT, {
                    'lat':    telem['lat'],
                    'lon':    telem['lon'],
                    'alt':    telem['alt_mm'],
                    'vx':     int(telem['vx'] * 100),
                    'vy':     int(telem['vy'] * 100),
                    'vz':     int(telem['vz'] * 100),
                    'hdg':    int(math.degrees(telem['yaw']) * 100) % 36000,
                })

            # Attitude (10 Hz)
            if self._t - _last_att >= _att_interval:
                yield self._make_packet(MSG_ATTITUDE, {
                    'roll':       telem['roll'],
                    'pitch':      telem['pitch'],
                    'yaw':        telem['yaw'],
                    'rollspeed':  self.rng.gauss(0, 0.01),
                    'pitchspeed': self.rng.gauss(0, 0.01),
                    'yawspeed':   self.rng.gauss(0, 0.005),
                })
                _last_att = self._t

            # Heartbeat (1 Hz)
            if self._t - _last_hb >= _hb_interval:
                yield self._make_packet(MSG_HEARTBEAT, {
                    'type':             2,      # MAV_TYPE_QUADROTOR
                    'autopilot':        3,      # MAV_AUTOPILOT_ARDUPILOTMEGA
                    'base_mode':        209,    # Armed + stabilize
                    'system_status':    4,      # MAV_STATE_ACTIVE
                    'mavlink_version':  3,
                })
                _last_hb = self._t

            self._t = round(self._t + self._dt, 4)
