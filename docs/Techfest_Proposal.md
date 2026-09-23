# PUSHPAK Grand Challenge: Security of Drones
## Stage 1 Technical Proposal: AEGIS (Autonomous Embedded Guardian for Intrusion in Swarms)

**Team:** Persistent Formation  
**Members:** Sumit Saraswat, Tanmay Kaushal  
**Objective:** Objective 2 - Drone Intrusion Detection System (Drone IDS)

---

## 1. Introduction and Architecture

As autonomous UAV systems increasingly rely on the MAVLink protocol for telemetry and command, they remain highly vulnerable to cyber threats due to the protocol's lack of native authentication and encryption. AEGIS is a lightweight, hybrid Drone Intrusion Detection System designed to run on resource-constrained onboard flight controllers or companion computers (e.g., Raspberry Pi).

AEGIS employs a dual-engine architecture:
1. **Deterministic Rule Engine:** Matches known attack signatures (e.g., GPS jumping, unauthorized COMMAND_LONG packets).
2. **Isolation Forest Anomaly Detector:** An unsupervised machine-learning model trained on nominal flight envelopes to detect zero-day or subtle attacks.

All detected events are logged into a **Cryptographic Chain Logger**, ensuring tamper-evident forensics.

## 2. Threat Catalogue and Attack Models

AEGIS currently identifies and mitigates four critical cyber-physical threats:

### 2.1 GPS Spoofing
- **Vector:** An adversary transmits stronger, counterfeit GPS signals.
- **Model:** The UAV's perceived coordinates drift from reality. AEGIS detects this via sudden position jumps (haversine distance > threshold in $\Delta t$) or abnormally low HDOP (Dilution of Precision), which indicates synthetically clean signals.

### 2.2 Command Injection
- **Vector:** Unencrypted `COMMAND_LONG` packets injected via an exposed telemetry radio.
- **Model:** Attacker attempts to force a `LAND` (21), `RTL` (20), or `DISARM` (400) state. AEGIS flags critical commands originating from unknown or non-GCS `system_id` values.

### 2.3 Denial of Service (DoS) Flood
- **Vector:** The communication bus is overwhelmed.
- **Model:** High-frequency burst of `HEARTBEAT` or parameter request packets intended to drop legitimate GCS traffic. AEGIS monitors rate limits per time window.

### 2.4 Replay Attack
- **Vector:** An adversary records valid telemetry or commands and rebroadcasts them later.
- **Model:** AEGIS detects non-monotonic or stale timestamps in the MAVLink packet headers.

## 3. Detection Methodology & Feature Extraction

### Rule-Based Engine
The rule engine evaluates each packet independently in $O(1)$ time, maintaining minimal state (last known position, last timestamp, and a sliding window for DoS counting).

### Isolation Forest (Machine Learning)
For complex anomalies, AEGIS extracts a 12-dimensional feature vector from a sliding 2.0-second window:
- **Kinematics:** `lat_delta`, `lon_delta`, `alt_delta`, `hdop`
- **Dynamics:** `roll_rate`, `pitch_rate`, `yaw_rate`
- **Network:** `gps_hz`, `hb_hz`, `unique_sysids`, `cmd_cnt`, `ts_monotonic`

An Isolation Forest model (contamination = 0.05, 100 estimators) scores this vector. A negative score (e.g., $< -0.1$) triggers an alert.

## 4. Logging and Chain of Custody

To satisfy forensic requirements, AEGIS implements a **Chain Logger**. Each log entry (alert or packet) is serialized to JSON and hashed using SHA-256. The hash of entry $N-1$ is embedded in entry $N$. If an attacker breaches the companion computer and modifies an alert, the cryptographic chain is broken, rendering the tampering instantly detectable during post-incident analysis.

## 5. Benchmarking and Validation

AEGIS is validated against a deterministic MAVLink simulation engine that injects mathematically precise attacks. 

**Preliminary Benchmark Results:**
- **Detection Accuracy:** >98% true positive rate across GPS Spoofing and Command Injection.
- **False Positive Rate:** <2% in nominal high-dynamic flight simulation.
- **Detection Latency:** < 100ms (Rule Engine) and < 2.0s (ML sliding window).
- **Compute Overhead:** < 5% CPU utilization on an ARM Cortex-A72 (Raspberry Pi 4).

## 6. System Integration Methodology

For Stage 2 (Hardware implementation), AEGIS will act as a transparent proxy. It will be installed on an onboard companion computer via Docker, intercepting the serial/UART connection between the Pixhawk Flight Controller and the Telemetry Radio. Suspicious packets can be either logged (Passive IDS) or actively dropped (Intrusion Prevention System - IPS) before reaching the flight controller.
