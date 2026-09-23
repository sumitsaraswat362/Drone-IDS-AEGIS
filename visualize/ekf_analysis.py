"""
AEGIS — EKF Innovation & Mahalanobis Distance Plotter
Generates publication-quality plots of the EKF innovation residuals
and the Mahalanobis distance envelope, showing exactly when
the χ² threshold is crossed during a GPS spoofing attack.

Usage:
    python3 visualize/ekf_analysis.py --scenario scenarios/gps_spoofing.yaml
"""
import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.simulator.attack_injector import AttackInjector
from src.detection.ekf_twin import EKFCyberTwin
from src.simulator.mavlink_simulator import MSG_GPS_RAW_INT

CHI2_THRESHOLD = 16.27   # 3 DOF, 99.9% confidence


def run_ekf_analysis(scenario: dict, out_path: str = "logs/ekf_analysis.png"):
    injector = AttackInjector(scenario=scenario, seed=scenario.get("seed", 42))
    ekf      = EKFCyberTwin()

    timestamps   = []
    mahal_scores = []
    is_attack    = []

    for pkt in injector.stream():
        if pkt.msg_id != MSG_GPS_RAW_INT:
            continue
        if not ekf.initialized:
            ekf.process_packet(pkt)
            continue

        import copy
        pkt_copy = copy.deepcopy(pkt)
        t  = pkt.timestamp_s
        dt = max(t - ekf.last_ts, 1e-6)
        ekf.predict(dt)

        lat = pkt.payload.get('lat', 0)
        lon = pkt.payload.get('lon', 0)
        alt = pkt.payload.get('alt', 0) / 1000.0

        import math
        REF_LAT, REF_LON = 19.1334, 72.9133
        dx = (lon/1e7 - REF_LON) * 111000.0 * math.cos(math.radians(REF_LAT))
        dy = (lat/1e7 - REF_LAT) * 111000.0
        z  = np.array([[dx], [dy], [alt]])

        score = ekf.update(z)
        ekf.last_ts = t

        timestamps.append(t)
        mahal_scores.append(min(score, 60))  # Cap for readability
        is_attack.append(pkt.is_attack)

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), facecolor='#0a0a0a')
    fig.suptitle("AEGIS — EKF Digital Twin: Mahalanobis Distance Analysis",
                 color='white', fontsize=14, fontweight='bold')

    t_arr = np.array(timestamps)
    m_arr = np.array(mahal_scores)
    atk_mask = np.array(is_attack)

    # Top: Mahalanobis distance over time
    ax1 = axes[0]
    ax1.set_facecolor('#0f0f0f')
    ax1.plot(t_arr, m_arr, color='#00d4ff', linewidth=1.5, label='Mahalanobis Distance d²', alpha=0.9)
    ax1.axhline(CHI2_THRESHOLD, color='#ff4444', linewidth=1.5, linestyle='--',
                label=f'χ² Threshold (3 DOF, 99.9%) = {CHI2_THRESHOLD}')
    ax1.fill_between(t_arr, m_arr, CHI2_THRESHOLD,
                     where=(m_arr > CHI2_THRESHOLD), color='#ff4444', alpha=0.2,
                     label='Attack Detected Region')
    ax1.fill_between(t_arr, 0, 2, where=atk_mask, color='#ff8800', alpha=0.15,
                     label='True Attack Window')
    ax1.set_ylabel('d² (Mahalanobis)', color='#aaaaaa')
    ax1.tick_params(colors='#666666')
    ax1.spines['bottom'].set_color('#333333'); ax1.spines['top'].set_color('#333333')
    ax1.spines['left'].set_color('#333333'); ax1.spines['right'].set_color('#333333')
    ax1.legend(loc='upper left', facecolor='#111111', edgecolor='#333333',
               labelcolor='white', fontsize=9)
    ax1.grid(color='#222222', linestyle='--', linewidth=0.5)

    # Bottom: Attack classification binary
    ax2 = axes[1]
    ax2.set_facecolor('#0f0f0f')
    detected = (m_arr > CHI2_THRESHOLD).astype(int)
    ax2.fill_between(t_arr, 0, atk_mask.astype(int), color='#ff8800', alpha=0.4, label='Ground Truth Attack')
    ax2.fill_between(t_arr, 0, detected, color='#00ff88', alpha=0.4, label='AEGIS Detection')
    ax2.set_xlabel('Simulation Time (s)', color='#aaaaaa')
    ax2.set_ylabel('0=Clean / 1=Attack', color='#aaaaaa')
    ax2.tick_params(colors='#666666')
    ax2.spines['bottom'].set_color('#333333'); ax2.spines['top'].set_color('#333333')
    ax2.spines['left'].set_color('#333333'); ax2.spines['right'].set_color('#333333')
    ax2.legend(loc='upper left', facecolor='#111111', edgecolor='#333333',
               labelcolor='white', fontsize=9)
    ax2.grid(color='#222222', linestyle='--', linewidth=0.5)
    ax2.set_ylim(-0.1, 1.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, facecolor='#0a0a0a', bbox_inches='tight')
    print(f"[AEGIS-VIZ] EKF analysis plot saved → {out_path}")
    try:
        plt.show()
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="scenarios/gps_spoofing.yaml")
    parser.add_argument("--out", default="logs/ekf_analysis.png")
    args = parser.parse_args()
    with open(args.scenario) as f:
        sc = yaml.safe_load(f)
    run_ekf_analysis(sc, out_path=args.out)
