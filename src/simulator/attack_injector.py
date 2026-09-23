"""
AEGIS Drone IDS — Attack Injector
Injects representative cyber attacks into a MAVLink packet stream.
Supports: GPS Spoofing, Command Injection, Denial-of-Service, Replay Attack.
"""
import copy
import math
import random
import time
from typing import Iterator, List
from .mavlink_simulator import MAVLinkPacket, MAVLinkSimulator, MSG_GPS_RAW_INT, \
    MSG_COMMAND_LONG, MSG_HEARTBEAT, MSG_GLOBAL_POSITION_INT, MSG_PARAM_SET


class AttackInjector:
    """
    Wraps a MAVLinkSimulator and injects attacks at specified times.

    Attack types implemented:
    ┌─────────────────────┬──────────────────────────────────────────────────┐
    │ Attack              │ Mechanism                                         │
    ├─────────────────────┼──────────────────────────────────────────────────┤
    │ GPS Spoofing        │ Replaces lat/lon/alt with fabricated coordinates  │
    │ Command Injection   │ Injects forged COMMAND_LONG (e.g. land, disarm)  │
    │ Denial-of-Service   │ Floods channel with high-rate heartbeats          │
    │ Replay Attack       │ Re-sends previously captured valid packets        │
    └─────────────────────┴──────────────────────────────────────────────────┘
    """

    def __init__(self, scenario: dict, seed: int = 42):
        """
        scenario dict keys:
          duration_s   : total mission length in seconds
          seed         : RNG seed for reproducibility
          attacks      : list of dicts with keys:
                           type   : 'gps_spoof' | 'cmd_inject' | 'dos' | 'replay'
                           start_s: attack start time (s)
                           end_s  : attack end time (s)
                           params : dict of attack-specific parameters
        """
        self.scenario = scenario
        self.rng      = random.Random(seed)
        self._replay_buffer: List[MAVLinkPacket] = []

    def _is_active(self, attack: dict, t: float) -> bool:
        return attack['start_s'] <= t <= attack['end_s']

    def _attack_gps_spoof(self, pkt: MAVLinkPacket, params: dict) -> MAVLinkPacket:
        """
        GPS Spoofing: gradually drift coordinates towards a fake location.
        The drift is subtle at first (mimicking real GPS error) then jumps.
        """
        fake = copy.deepcopy(pkt)
        fake.is_attack   = True
        fake.attack_type = 'GPS_SPOOFING'

        # Target fake coords (Mumbai airport for realism)
        target_lat = int(19.0896 * 1e7)
        target_lon = int(72.8656 * 1e7)
        spoof_intensity = params.get('intensity', 1.0)   # 0-1

        fake.payload['lat'] = int(pkt.payload['lat'] + (target_lat - pkt.payload['lat']) * spoof_intensity * 0.3)
        fake.payload['lon'] = int(pkt.payload['lon'] + (target_lon - pkt.payload['lon']) * spoof_intensity * 0.3)
        fake.payload['alt'] = int(pkt.payload.get('alt', 50000) * (1 + spoof_intensity * 0.5))
        # Spoofed GPS often has abnormally good HDOP (too clean)
        fake.payload['eph'] = int(fake.payload.get('eph', 120) * 0.2)
        return fake

    def _attack_cmd_inject(self, t: float, seq: int, params: dict) -> MAVLinkPacket:
        """
        Command Injection: forge a COMMAND_LONG from the attacker (system_id=99).
        Commands: 20=RTL, 21=LAND, 400=COMPONENT_ARM_DISARM(disarm).
        """
        cmd = params.get('command_id', 21)   # default: LAND
        return MAVLinkPacket(
            timestamp_s  = t,
            msg_id       = MSG_COMMAND_LONG,
            system_id    = 99,           # Attacker spoofed GCS ID
            component_id = 1,
            sequence     = seq % 256,
            payload      = {
                'target_system':    1,
                'target_component': 1,
                'command':          cmd,
                'confirmation':     0,
                'param1':           0.0,
                'param2':           0.0,
                'param3':           0.0,
                'param4':           0.0,
                'param5':           0.0,
                'param6':           0.0,
                'param7':           0.0,
            },
            is_attack    = True,
            attack_type  = 'COMMAND_INJECTION',
        )

    def _attack_dos_flood(self, t: float, seq_start: int, params: dict) -> List[MAVLinkPacket]:
        """
        Denial-of-Service: flood with hundreds of heartbeats in a single tick.
        Rate: configurable, default 200 pkts/s burst.
        """
        burst = params.get('burst_count', 50)
        pkts  = []
        for i in range(burst):
            pkts.append(MAVLinkPacket(
                timestamp_s  = round(t + i * 0.001, 4),
                msg_id       = MSG_HEARTBEAT,
                system_id    = self.rng.randint(200, 254),   # Random attacker IDs
                component_id = 1,
                sequence     = (seq_start + i) % 256,
                payload      = {
                    'type':            6,    # MAV_TYPE_GCS
                    'autopilot':       0,
                    'base_mode':       0,
                    'system_status':   0,
                    'mavlink_version': 3,
                },
                is_attack    = True,
                attack_type  = 'DENIAL_OF_SERVICE',
            ))
        return pkts

    def _attack_replay(self, t: float, seq: int) -> List[MAVLinkPacket]:
        """
        Replay Attack: re-transmit previously captured valid packets with
        original timestamps, but injected at current time.
        """
        if not self._replay_buffer:
            return []
        pkts = []
        for original in self.rng.sample(self._replay_buffer, min(5, len(self._replay_buffer))):
            replayed = copy.deepcopy(original)
            # Key tell: packet timestamp does NOT match current time
            replayed.is_attack   = True
            replayed.attack_type = 'REPLAY_ATTACK'
            # We keep the OLD timestamp — this is how replays are detected
            pkts.append(replayed)
        return pkts

    def stream(self) -> Iterator[MAVLinkPacket]:
        """
        Yield packets from the underlying simulator, injecting attacks
        at the configured times.
        """
        sim      = MAVLinkSimulator(duration_s=self.scenario.get('duration_s', 120),
                                    seed=self.scenario.get('seed', 42))
        attacks  = self.scenario.get('attacks', [])
        _seq_ctr = 0

        for pkt in sim.stream():
            t = pkt.timestamp_s

            # Buffer clean packets for replay attack
            if not pkt.is_attack and len(self._replay_buffer) < 50:
                self._replay_buffer.append(copy.deepcopy(pkt))

            # Check each attack
            for atk in attacks:
                if not self._is_active(atk, t):
                    continue
                atype  = atk['type']
                params = atk.get('params', {})

                if atype == 'gps_spoof' and pkt.msg_id in (MSG_GPS_RAW_INT, MSG_GLOBAL_POSITION_INT):
                    pkt = self._attack_gps_spoof(pkt, params)

                elif atype == 'cmd_inject' and pkt.msg_id == MSG_HEARTBEAT:
                    # Inject forged command alongside legitimate heartbeat
                    yield self._attack_cmd_inject(t, _seq_ctr, params)
                    _seq_ctr += 1

                elif atype == 'dos' and pkt.msg_id == MSG_HEARTBEAT:
                    # Emit flood burst
                    for flood_pkt in self._attack_dos_flood(t, _seq_ctr, params):
                        yield flood_pkt
                    _seq_ctr += params.get('burst_count', 50)

                elif atype == 'replay' and pkt.msg_id == MSG_GPS_RAW_INT:
                    for rp in self._attack_replay(t, _seq_ctr):
                        yield rp
                    _seq_ctr += 5

            yield pkt
            _seq_ctr += 1
