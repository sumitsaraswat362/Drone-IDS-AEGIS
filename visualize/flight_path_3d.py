"""
AEGIS — 3D MAVLink Flight Path Visualizer (Matplotlib/mpl_toolkits)
Renders a 3D animated reconstruction of the UAV's true vs. spoofed trajectory,
with the EKF Digital Twin's predicted corridor overlaid.

Usage:
    python3 visualize/flight_path_3d.py --scenario scenarios/gps_spoofing.yaml
"""
import sys
import os
import math
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.simulator.mavlink_simulator import MAVLinkSimulator, MSG_GPS_RAW_INT
from src.simulator.attack_injector import AttackInjector
from src.detection.ekf_twin import EKFCyberTwin

matplotlib.use('TkAgg') if sys.platform == 'darwin' else matplotlib.use('Agg')


def collect_trajectories(scenario: dict):
    """Run the sim and collect true & spoofed GPS trajectories with EKF prediction."""
    true_xs, true_ys, true_zs   = [], [], []
    spoof_xs, spoof_ys, spoof_zs = [], [], []
    ekf_xs, ekf_ys, ekf_zs      = [], [], []
    attack_ts                    = []

    injector = AttackInjector(scenario=scenario, seed=scenario.get("seed", 42))
    ekf      = EKFCyberTwin()

    REF_LAT = 19.1334
    REF_LON = 72.9133

    def latlon_to_m(lat_e7, lon_e7):
        lat = lat_e7 / 1e7
        lon = lon_e7 / 1e7
        x = (lon - REF_LON) * 111000.0 * math.cos(math.radians(REF_LAT))
        y = (lat - REF_LAT) * 111000.0
        return x, y

    for pkt in injector.stream():
        if pkt.msg_id != MSG_GPS_RAW_INT:
            continue

        lat = pkt.payload.get('lat', 0)
        lon = pkt.payload.get('lon', 0)
        alt = pkt.payload.get('alt', 0) / 1000.0
        x, y = latlon_to_m(lat, lon)

        if pkt.is_attack:
            spoof_xs.append(x); spoof_ys.append(y); spoof_zs.append(alt)
            attack_ts.append(pkt.timestamp_s)
        else:
            true_xs.append(x); true_ys.append(y); true_zs.append(alt)

        ekf.process_packet(pkt)
        if ekf.initialized:
            ekf_xs.append(float(ekf.x[0])); ekf_ys.append(float(ekf.x[1])); ekf_zs.append(float(ekf.x[2]))

    return (true_xs, true_ys, true_zs), (spoof_xs, spoof_ys, spoof_zs), (ekf_xs, ekf_ys, ekf_zs)


def plot_3d(scenario: dict, out_path: str = "logs/flight_path_3d.png"):
    (tx, ty, tz), (sx, sy, sz), (ex, ey, ez) = collect_trajectories(scenario)

    fig = plt.figure(figsize=(14, 10), facecolor='#0a0a0a')
    ax  = fig.add_subplot(111, projection='3d', facecolor='#0a0a0a')

    ax.set_facecolor('#0a0a0a')
    ax.tick_params(colors='#666666')
    for spine in ax.spines.values():
        spine.set_edgecolor('#333333')
    ax.xaxis.pane.fill = False; ax.yaxis.pane.fill = False; ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('#222222')
    ax.yaxis.pane.set_edgecolor('#222222')
    ax.zaxis.pane.set_edgecolor('#222222')
    ax.grid(color='#222222', linestyle='--', linewidth=0.5)

    # True GPS trajectory
    ax.plot(tx, ty, tz, color='#00d4ff', linewidth=2, label='True GPS Path', alpha=0.9)
    ax.scatter(tx[0], ty[0], tz[0], color='#00ff88', s=120, zorder=5, label='Takeoff')
    ax.scatter(tx[-1], ty[-1], tz[-1], color='#ffaa00', s=120, zorder=5, label='Landing')

    # Spoofed GPS trajectory
    if sx:
        ax.plot(sx, sy, sz, color='#ff4444', linewidth=2.5, linestyle='--',
                label='Spoofed GPS (Attack)', alpha=0.95)

    # EKF Digital Twin prediction corridor
    if ex:
        ax.plot(ex, ey, ez, color='#aa00ff', linewidth=1.5, linestyle=':', alpha=0.7,
                label='EKF Digital Twin Prediction')

    ax.set_xlabel('East (m)', color='#888888')
    ax.set_ylabel('North (m)', color='#888888')
    ax.set_zlabel('Altitude (m)', color='#888888')

    title = f"AEGIS — 3D Flight Reconstruction\n{scenario.get('name', 'Attack Scenario')}"
    ax.set_title(title, color='white', fontsize=13, pad=20)
    legend = ax.legend(loc='upper left', facecolor='#111111', edgecolor='#333333', labelcolor='white', fontsize=9)

    fig.tight_layout()
    plt.savefig(out_path, dpi=150, facecolor='#0a0a0a', bbox_inches='tight')
    print(f"[AEGIS-VIZ] 3D flight path saved → {out_path}")
    try:
        plt.show()
    except Exception:
        pass
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AEGIS 3D Flight Path Visualizer")
    parser.add_argument("--scenario", default="scenarios/gps_spoofing.yaml")
    parser.add_argument("--out", default="logs/flight_path_3d.png")
    args = parser.parse_args()

    with open(args.scenario) as f:
        sc = yaml.safe_load(f)
    plot_3d(sc, out_path=args.out)
