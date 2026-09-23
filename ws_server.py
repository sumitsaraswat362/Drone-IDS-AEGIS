"""
AEGIS — WebSocket Server
Streams real-time AEGIS detection events to the Next.js dashboard.
The dashboard connects via ws://localhost:8765 and receives JSON alerts.
"""
import asyncio
import json
import sys
import os
import time
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import websockets
except ImportError:
    os.system(f"{sys.executable} -m pip install websockets -q")
    import websockets

from src.simulator.mavlink_simulator import MAVLinkSimulator
from src.simulator.attack_injector import AttackInjector
from src.detection.rule_engine import RuleEngine
from src.detection.anomaly_detector import AnomalyDetector
from src.detection.ekf_twin import EKFCyberTwin
from src.core.logger import ChainLogger

CONNECTED_CLIENTS = set()

async def broadcast(message: dict):
    if CONNECTED_CLIENTS:
        data = json.dumps(message)
        await asyncio.gather(*[client.send(data) for client in list(CONNECTED_CLIENTS)], return_exceptions=True)

async def run_ids_stream(scenario: dict):
    """Run the AEGIS pipeline and broadcast events to all dashboard clients."""
    rule_engine = RuleEngine()
    anomaly_det = AnomalyDetector(random_state=42)
    ekf_twin    = EKFCyberTwin()
    logger      = ChainLogger(log_path=f"logs/ws_session_{int(time.time())}_events.jsonl")

    # Train ML baseline
    clean_sim = MAVLinkSimulator(duration_s=30, seed=999)
    anomaly_det.feed_normal(list(clean_sim.stream()))
    anomaly_det.train()

    await broadcast({"type": "STATUS", "payload": {"status": "ARMED", "message": "AEGIS IDS Online — Monitoring MAVLink stream"}})

    injector = AttackInjector(scenario=scenario, seed=scenario.get("seed", 42))
    pkt_count = 0

    for pkt in injector.stream():
        pkt_count += 1

        ekf_score = None
        if hasattr(ekf_twin, 'initialized') and ekf_twin.initialized:
            import numpy as np, math, copy
            t, dt = pkt.timestamp_s, max(pkt.timestamp_s - ekf_twin.last_ts, 1e-6)
            ekf_twin.predict(dt)
            lat, lon = pkt.payload.get('lat', 0), pkt.payload.get('lon', 0)
            alt = pkt.payload.get('alt', 0) / 1000.0
            REF_LAT, REF_LON = 19.1334, 72.9133
            dx = (lon/1e7 - REF_LON) * 111000 * math.cos(math.radians(REF_LAT))
            dy = (lat/1e7 - REF_LAT) * 111000
            z  = np.array([[dx],[dy],[alt]])
            ekf_score = ekf_twin.update(z)
            ekf_twin.last_ts = t
        else:
            ekf_twin.process_packet(pkt)

        # Broadcast telemetry every 10 packets
        if pkt_count % 10 == 0:
            await broadcast({
                "type": "TELEMETRY",
                "payload": {
                    "timestamp_s": pkt.timestamp_s,
                    "packets": pkt_count,
                    "lat": pkt.payload.get('lat', 0) / 1e7,
                    "lon": pkt.payload.get('lon', 0) / 1e7,
                    "alt_m": pkt.payload.get('alt', 0) / 1000.0,
                    "mahalanobis": round(ekf_score or 0.0, 3),
                    "chi2_threshold": 16.27,
                    "is_attack": pkt.is_attack,
                }
            })

        # Alerts
        for alert_fn, label in [
            (lambda p: rule_engine.process(p), "RULE_ENGINE"),
            (lambda p: anomaly_det.score_packet(p), "ISOLATION_FOREST"),
        ]:
            alert = alert_fn(pkt)
            if alert:
                alert["detector"] = label
                logger.log_alert(alert)
                await broadcast({"type": "ALERT", "payload": alert})
                await broadcast({"type": "STATUS", "payload": {"status": "THREAT_DETECTED"}})

        if ekf_score and ekf_score > 16.27:
            ekf_alert = {
                "rule": "EKF_DIGITAL_TWIN_ANOMALY", "severity": "CRITICAL",
                "timestamp_s": pkt.timestamp_s, "detector": "EKF_DIGITAL_TWIN",
                "detail": f"Mahalanobis d²={ekf_score:.2f} > 16.27. NavIC/GPS spoofing detected.",
                "sha256": pkt.sha256(),
            }
            logger.log_alert(ekf_alert)
            await broadcast({"type": "ALERT", "payload": ekf_alert})

        await asyncio.sleep(0.005)   # 200 pkt/s max rate for WS

    await broadcast({"type": "STATUS", "payload": {"status": "MISSION_COMPLETE"}})
    logger.close()

async def handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"[WS] Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "START_SCENARIO":
                scenario_name = data.get("scenario", "scenarios/gps_spoofing.yaml")
                with open(scenario_name) as f:
                    scenario = yaml.safe_load(f)
                asyncio.create_task(run_ids_stream(scenario))
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        print(f"[WS] Client disconnected")

async def main():
    print("[AEGIS WS] Server starting on ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
