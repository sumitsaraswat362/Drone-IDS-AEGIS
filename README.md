# AEGIS: Drone Intrusion Detection System
**PUSHPAK Grand Challenge 2026: Security of Drones**  
**Team Persistent Formation**

AEGIS (Autonomous Embedded Guardian for Intrusion in Swarms) is a lightweight, hybrid MAVLink Intrusion Detection System designed for resource-constrained UAV flight controllers.

## Overview

AEGIS protects drones against 4 critical cyber-physical threats:
1. **GPS Spoofing**
2. **Command Injection (RTL/Land/Disarm spoofing)**
3. **Denial-of-Service (Packet Flooding)**
4. **Replay Attacks**

It uses a dual-engine architecture:
- **Rule Engine:** Deterministic, $O(1)$ signature matching for immediate threat isolation.
- **Isolation Forest ML:** Unsupervised anomaly detection for zero-day attack vectors based on flight kinematic features.
- **Cryptographic Chain Logger:** A tamper-evident logging system ensuring chain-of-custody for forensic analysis.

## Setup & Installation

```bash
# 1. Clone repository
git clone https://github.com/sumitsaraswat362/Drone-IDS-AEGIS.git
cd Drone-IDS-AEGIS

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Running the Simulation

AEGIS includes a deterministic MAVLink v2 attack simulator. You can run pre-configured attack scenarios to test the IDS accuracy.

```bash
# Test GPS Spoofing Attack
python3 main.py --scenario scenarios/gps_spoofing.yaml

# Test Command Injection Attack
python3 main.py --scenario scenarios/command_injection.yaml

# Test DoS Attack
python3 main.py --scenario scenarios/dos_attack.yaml
```

The output will provide a detailed metric breakdown (Precision, Recall, F1 Score, and Detection Latency), and the raw tamper-evident logs will be saved to the `logs/` directory.

## Repository Structure
- `src/simulator/`: Realistic UAV physics model and MAVLink packet attack injector.
- `src/detection/`: The core Rule Engine and Isolation Forest anomaly detector.
- `src/core/`: The IDS orchestrator and Cryptographic Chain Logger.
- `scenarios/`: YAML configurations for different attack vectors.
- `docs/`: Technical proposals and architecture diagrams.
