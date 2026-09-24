# 🎬 AEGIS: Official Stage 1 Pitch Video Script

**Target Duration:** ~3 Minutes (Fast-paced, high energy)
**Audience:** Prof. Arnab Maity (Aerospace GNC) & Prof. Faruk Kazi (Cyber-Physical Security)

---

## 🎥 0:00 - 0:35 | The Hook & The Physics (Face Camera)

**[VISUAL: You on camera, looking confident. No screen sharing yet.]**

**Speaker:**
"Hello judges, I am Sumit Saraswat from Team Persistent Formation. Today we are presenting AEGIS — an Autonomous Embedded Guardian for Intrusion in Swarms. 

Right now, the drone industry has a massive blind spot. Current Drone IDS solutions try to apply basic IT network rules to UAVs. They fail because they don't understand physics. A drone accelerating at 5 meters per second squared is normal; but a drone teleporting 200 meters instantly? That is a GPS spoofing attack. 

We solved this by fusing aerospace estimation theory with cyber-security. AEGIS is a Tri-Engine IDS powered by a Kinematic Extended Kalman Filter, an Isolation Forest ML model, and a Cryptographic Chain Logger. Let me show you how it works."

---

## 💻 0:35 - 1:25 | The EKF Digital Twin Demo (Screen Record)

**[VISUAL: Switch to Screen Recording. Open `https://ageis-ecru.vercel.app` on the LIVE MONITOR tab.]**

**Speaker:**
"This is the AEGIS Command Center. I'll launch a simulated flight."

**[ACTION: Click 'Launch Simulation' for GPS/NavIC Spoofing]**

**Speaker:**
"Right now, the drone is flying normally. Under the hood, our Extended Kalman Filter is tracking the drone's 6-Degree-of-Freedom state vector in real-time."

**[VISUAL: Wait for the attack to trigger at t=5s. The screen flashes red, Critical Alerts populate the log.]**

**Speaker:**
"And there is the attack. An adversary just injected a spoofed NavIC coordinate. Standard rule engines generate massive false positives here. But let's look at the math."

**[ACTION: Click the 'EKF Twin' tab on the left to show the big Mahalanobis chart]**

**Speaker:**
"AEGIS computes the Mahalanobis distance of the sensor innovation residual. Look at this chart: the moment the spoofed packet arrived, the residual distance violently spiked past our 99.9% Chi-Squared confidence threshold of 16.27. We didn't just guess there was an anomaly; we mathematically *proved* the sensor reading violated the physical kinematic envelope of the UAV."

---

## 🔍 1:25 - 2:05 | Cyber-Physical Forensics & ML (Screen Record)

**[ACTION: Click the 'Forensics' tab on the left]**

**Speaker:**
"To ensure absolute evidence integrity for post-incident analysis, AEGIS uses a Cryptographic Chain Logger. Every alert is hashed using SHA-256 and chained to the previous block. If an attacker compromises the companion computer and tries to erase their tracks, the hash chain breaks, making tampering mathematically evident."

**[ACTION: Go back to 'Live Monitor' and click 'Launch Simulation' for DoS Heartbeat Flood]**

**Speaker:**
"Our Tri-Engine architecture also handles standard network exploits instantly. Here, we inject a MAVLink Heartbeat Flood. Our deterministic Rule Engine catches the bus saturation in under 100 milliseconds, completely bypassing the heavier ML pipeline to save vital CPU cycles on the companion computer."

---

## 📈 2:05 - 2:40 | Statistical Proof (Screen Record)

**[VISUAL: Show the `Stage1_Report.pdf` on the screen, scrolled down to Section 6.1: Monte Carlo Validation table]**

**Speaker:**
"We didn't just build a flashy dashboard; we rigorously validated these algorithms. We ran a 400-seed Monte Carlo simulation across 4 distinct attack vectors to ensure absolute reproducibility.

As you can see in our report, our EKF and Rule engines achieved a 99.5% recall on Denial of Service attacks and completely isolated Command Injections with a 16% False Positive Rate constraint. We proved it works mathematically before writing a single line of hardware code."

---

## 🏁 2:40 - 3:00 | The Close (Face Camera)

**[VISUAL: Switch back to you on camera.]**

**Speaker:**
"AEGIS is fully open-source and ready for Stage 2 hardware integration on Pixhawk and Raspberry Pi companion computers. By fusing aerospace Estimation Theory with zero-trust cyber-physical security, we've built a Drone IDS that actually understands how drones fly. 

Thank you for your time."
