<div align="center">

<img src="https://img.shields.io/badge/AEGIS-v1.0.0-brightgreen?style=for-the-badge&logo=shield&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Platform-ArduPilot%20%7C%20PX4-orange?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Protocol-MAVLink%20v2-cyan?style=for-the-badge"/>
<img src="https://img.shields.io/badge/ML-Isolation%20Forest-purple?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Dashboard-Live%20on%20Vercel-black?style=for-the-badge&logo=vercel"/>

<br/><br/>

# 🛡️ AEGIS — Autonomous Embedded Guardian for Intrusion in Swarms

### A Cyber-Physical Digital Twin Intrusion Detection System for MAVLink UAVs

**Team: Acrobats** | PUSHPAK Grand Challenge 2026 — Security of Drones (Objective 2)

[**🔴 Live Dashboard →**](https://ageis-ecru.vercel.app) &nbsp;|&nbsp; [**📄 Stage 1 Report →**](docs/Stage1_Report.md) &nbsp;|&nbsp; [**📐 Architecture →**](docs/Techfest_Proposal.md)

</div>

---

## 📌 Abstract

MAVLink — the protocol powering PX4, ArduPilot, and virtually all civilian and defence UAVs — was designed for efficiency, **not security**. It has no authentication, no encryption, and no replay protection. An adversary with a \$30 SDR dongle and line-of-sight can intercept, forge, and replay any command.

AEGIS addresses this with a **Cyber-Physical Digital Twin** approach, moving far beyond static IP-based IDS rules. Rather than asking *"does this packet look suspicious?"*, AEGIS asks **"does this sensor reading comply with the laws of physics?"**

The core is a **Kinematic Extended Kalman Filter (EKF)** that tracks the UAV's 6-DOF state in real-time. Incoming NavIC/GPS telemetry is evaluated using the **Mahalanobis Distance** — a statistically rigorous test from aerospace GNC theory. Combined with an **Isolation Forest** ML anomaly detector and a zero-latency rule engine, AEGIS detects all four major MAVLink attack vectors with surgical precision.

---

## 🏛️ Architecture: The Three Detection Engines

```
  MAVLink v2 Telemetry Stream (from Pixhawk / SITL)
                    │
           ┌────────┴────────┐
           ▼                 ▼
  ┌──────────────┐  ┌───────────────────────────┐
  │ Rule Engine  │  │  EKF Kinematic Digital Twin│  ← Core Innovation
  │  (O(1)/pkt)  │  │  State: [x,y,z,vx,vy,vz]  │
  │              │  │  Mahalanobis d² vs χ²(3DOF)│
  │ R1: GPS Jump │  └───────────┬───────────────┘
  │ R4: DoS Flood│              │
  │ R5: Rogue CMD│  ┌───────────▼───────────────┐
  │ R6: Replay   │  │  Isolation Forest ML (100  │
  │ R7: GCS Imp. │  │  estimators, 12-dim feats) │
  └──────┬───────┘  └───────────┬───────────────┘
         └──────────┬───────────┘
                    ▼
     ┌──────────────────────────────┐
     │ Cryptographic Chain Logger   │
     │ SHA-256 chain-of-custody     │
     │ (Tamper-evident forensics)   │
     └──────────────┬───────────────┘
                    ▼
     ┌──────────────────────────────┐
     │ Real-time WebSocket Server   │──► Next.js Dashboard
     │ ws://localhost:8765          │    ageis-ecru.vercel.app
     └──────────────────────────────┘
```

---

## 🔬 The EKF Digital Twin: Core Mathematical Foundation

The state vector tracked by AEGIS is:

$$X = [x, \; y, \; z, \; v_x, \; v_y, \; v_z]^T$$

**Predict step** (Constant Velocity model):

$$\hat{X}_{k|k-1} = F \hat{X}_{k-1|k-1}, \quad P_{k|k-1} = F P_{k-1|k-1} F^T + Q$$

**Update step** (on GPS packet arrival):

$$y = z - H\hat{X}_{k|k-1}, \quad S = HP_{k|k-1}H^T + R$$

$$d^2 = y^T S^{-1} y \quad \xrightarrow{\text{if } d^2 > 16.27} \quad \text{GPS SPOOF DETECTED}$$

The threshold $\chi^2_{0.999}(3) = 16.27$ ensures that **fewer than 1 in 1000 legitimate GPS readings will ever trigger a false alarm** regardless of how aggressively the drone maneuvers.

---

## 🎯 Attack Detection Coverage

| Attack Vector | Detection Engine | Latency | Severity |
|---|---|---|---|
| NavIC / GPS Spoofing | **EKF Digital Twin** (Mahalanobis) | < 1 pkt | CRITICAL |
| GPS HDOP Anomaly (synthetic signal) | Rule Engine R2 | < 1 pkt | HIGH |
| GCS Command Injection (LAND/RTL) | Rule Engine R5 + R7 | < 1 pkt | CRITICAL |
| Heartbeat Flood (DoS) | Rule Engine R4 | ~100ms | HIGH |
| Replay Attack | Rule Engine R6 | < 1 pkt | HIGH |
| Zero-day / Novel Anomalies | **Isolation Forest** ML | ~2s window | HIGH |

---

## 📊 Python 3D Visualizations

AEGIS includes publication-quality Python/Matplotlib visualizations:

### 3D Flight Path Reconstruction (Matplotlib `mpl_toolkits`)
```bash
pip install matplotlib
python3 visualize/flight_path_3d.py --scenario scenarios/gps_spoofing.yaml
```
Renders a 3D dark-mode plot showing:
- **True GPS trajectory** (cyan)
- **Spoofed trajectory** (red dashed)
- **EKF Digital Twin prediction corridor** (purple dotted)

### EKF Mahalanobis Distance Analysis (Matplotlib)
```bash
python3 visualize/ekf_analysis.py --scenario scenarios/gps_spoofing.yaml
```
Renders a publication-quality dual-panel plot showing the Mahalanobis distance $d^2$ time series alongside the ground truth attack window, demonstrating exact detection timing.

---

## 📈 Monte Carlo Validation (600 Runs, 5 Scenarios)

```bash
python3 tests/monte_carlo_validation.py
```

Executes **600 total runs** (5 scenarios × 120 seeds) and produces:
- `logs/validation/mc_summary.json` — full statistical summary with 95% CI
- `logs/validation/mc_raw_results.csv` — seed-by-seed reproducibility log

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/sumitsaraswat362/Drone-IDS-AEGIS.git && cd Drone-IDS-AEGIS

# 2. Install
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip setuptools
pip install -r requirements.txt

# 3. Run a detection scenario
python3 main.py --scenario scenarios/gps_spoofing.yaml

# 4. Start the real-time dashboard backend
pip install websockets
python3 ws_server.py   # ws://localhost:8765

# 5. Start the Next.js dashboard (separate terminal)
cd dashboard && npm install && npm run dev  # http://localhost:3000
```

---

## 📁 Repository Structure

```
Drone-IDS-AEGIS/
├── src/
│   ├── simulator/
│   │   ├── mavlink_simulator.py   # UAV physics + MAVLink v2 packet generator
│   │   └── attack_injector.py     # GPS spoof / cmd inject / DoS / replay
│   ├── detection/
│   │   ├── ekf_twin.py            # Kinematic EKF Digital Twin (core)
│   │   ├── rule_engine.py         # 7-rule deterministic engine
│   │   └── anomaly_detector.py    # Isolation Forest (12-dim features)
│   └── core/
│       ├── ids.py                 # AEGIS orchestrator
│       └── logger.py              # Cryptographic chain logger
├── visualize/
│   ├── flight_path_3d.py         # Matplotlib 3D trajectory reconstruction
│   └── ekf_analysis.py           # Mahalanobis distance time series plot
├── tests/
│   └── monte_carlo_validation.py  # 600-run statistical validation
├── scenarios/
│   ├── gps_spoofing.yaml
│   ├── command_injection.yaml
│   └── dos_attack.yaml
├── dashboard/                     # Next.js Real-Time Dashboard (Vercel)
├── docs/
│   ├── Stage1_Report.md           # Official Techfest Stage 1 report
│   └── Techfest_Proposal.md
├── ws_server.py                   # WebSocket server for dashboard
├── main.py                        # CLI entry point
├── requirements.txt
└── LICENSE                        # MIT
```

---

## 🏆 Judges' Research Alignment

- **Prof. Arnab Maity (IIT Bombay Aerospace):** AEGIS's EKF Digital Twin directly implements the Guidance, Navigation, and Control (GNC) estimation theory Prof. Maity publishes on. The Mahalanobis distance thresholding is a standard aerospace sensor fusion technique applied to cybersecurity for the first time.
- **Prof. Faruk Kazi (VJTI Mumbai):** AEGIS's Cryptographic Chain Logger mirrors the forensic chain-of-custody frameworks Prof. Kazi applies to ICS/SCADA. His work on GPS/NavIC security in smart grids directly informs our NavIC spoofing detection logic.

---

## 📜 License

MIT © 2026 Team Acrobats — Sumit Saraswat & Tanmay Kaushal
