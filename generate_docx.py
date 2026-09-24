from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

sections = doc.sections
for section in sections:
    section.page_width = Inches(8.5)
    section.page_height = Inches(11.0)
    section.top_margin = Inches(1.5)
    section.bottom_margin = Inches(1.5)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    
    # Header
    header = section.header
    header_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header_para.add_run()
    run.add_picture('header_banner.png', width=Inches(6.5)) # Fit exactly within margins
    
    # Footer
    footer = section.footer
    footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = footer_para.add_run()
    run2.add_picture('footer_banner.png', width=Inches(6.5)) # Fit exactly within margins

# Title
title = doc.add_heading('Stage 1 Participant Submission - Security of Drones (Objective 2)', level=1)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph()

# Table 1: Team Info
table = doc.add_table(rows=11, cols=2)
table.style = 'Table Grid'
records = [
    ('Team ID', 'PF-4029'),
    ('Team Name', 'Acrobats'),
    ('Institution / Organization', 'Independent Research Team'),
    ('Team Leader', 'Sumit Saraswat'),
    ('Team Members', 'Sumit Saraswat, Tanmay Kaushal'),
    ('Faculty / Industry Mentor, if any', 'None'),
    ('Email Address', 'sumitsaraswat362@gmail.com'),
    ('Contact Number', '+91 9999999999'),
    ('Proposed Design Name', 'AEGIS — Autonomous Embedded Guardian for Intrusion in Swarms'),
    ('Date of Submission', '27 September 2026'),
]
for i, (key, val) in enumerate(records):
    row = table.rows[i]
    row.cells[0].text = key
    row.cells[0].paragraphs[0].runs[0].bold = True
    row.cells[1].text = val

doc.add_paragraph()

# Sections
def add_section(title_text, body_text):
    h = doc.add_heading(title_text, level=2)
    p = doc.add_paragraph(body_text)
    
add_section('1. Executive Summary', 
    'AEGIS is a novel, production-grade Drone Intrusion Detection System (IDS) built on a Cyber-Physical Digital Twin architecture. Unlike conventional IT-oriented IDS solutions that apply static rules to network packets, AEGIS fuses aerospace Guidance, Navigation, and Control (GNC) principles with machine learning to monitor, detect, and classify cyber-threats against MAVLink-based UAVs in real-time.\n\n'
    'The key innovation is a Kinematic Extended Kalman Filter (EKF) that maintains a running physics-based prediction of the UAV\'s 6-DOF state (position and velocity). Sensor readings are compared against this prediction using the Mahalanobis Distance in a Chi-Squared statistical test. When the sensor reading becomes statistically incompatible with the UAV\'s physical dynamics, AEGIS raises a CRITICAL alert.\n\n'
    'Key Deliverables include a Tri-engine detection pipeline, a Tamper-evident Cryptographic Chain Logger, a Live Vercel dashboard with WebSocket backend, and a 400-run Monte Carlo validation.'
)

add_section('2. Understanding of the Problem', 
    'The MAVLink protocol, the dominant UAV communication protocol, has no native authentication, encryption, or replay protection. Existing network IDS (like Snort) are designed for TCP/IP and have no understanding of UAV physics. A drone accelerating rapidly is normal, but teleporting 200 meters in 0.1 seconds is a GPS spoof. A rule-based system alone generates false positives. The only correct solution is a physics-aware IDS that detects attacks based on kinematic violations.'
)

add_section('3. Proposed Drone Forensic Toolkit / IDS', 
    'AEGIS consists of a Tri-Engine Architecture:\n\n'
    '1. EKF Digital Twin (Primary Innovation): Tracks the UAV state vector [x, y, z, vx, vy, vz]. On receiving a GPS packet, the innovation residual and covariance are computed. If the Mahalanobis distance d^2 > 16.27 (99.9% confidence), it flags a NavIC/GPS spoof.\n\n'
    '2. Isolation Forest (ML Anomaly Detector): A 12-dimensional feature vector is extracted from a 2-second sliding window. An Isolation Forest scores live packets to catch novel zero-day anomalies.\n\n'
    '3. Deterministic Rule Engine: Fast O(1) checks for Command Injections (R5), DoS Floods (R4), and Replay attacks (R6).\n\n'
    'Forensic capabilities are handled by a Cryptographic Chain Logger that hashes every event with SHA-256 to ensure tamper-evident evidence.'
)

add_section('4. Data Analysis & Automated Forensic Reporting', 
    'When an anomaly is detected, AEGIS logs the precise Mahalanobis variance and triggered rules. The evidence is stored in a JSONL chain-of-custody format where each entry hashes the previous entry. A live WebSocket dashboard visualizes the EKF thresholds and threat radar in real-time, allowing operators to immediately isolate compromised drones.'
)

add_section('5. Development Plan', 
    '1. Core simulation engine + attack injector (Complete)\n'
    '2. EKF Digital Twin & Isolation Forest (Complete)\n'
    '3. Real-Time WebSocket Dashboard (Complete)\n'
    '4. 400-run Monte Carlo Validation (Complete)\n'
    '5. Hardware integration on Pixhawk + RPi4 (Oct-Nov 2026)\n'
    '6. Live demo at Techfest (Dec 2026)'
)

doc.add_heading('6. Validation & Testing Methodology', level=2)
doc.add_paragraph('AEGIS was statistically validated across 400 simulation runs. The following test cases demonstrate the system\'s accuracy.')

# Test Case Table
tc_table = doc.add_table(rows=7, cols=5)
tc_table.style = 'Table Grid'
headers = ['Test ID', 'Test Description', 'Input Evidence', 'Expected Result', 'Success Criteria']
for i, h in enumerate(headers):
    tc_table.rows[0].cells[i].text = h
    tc_table.rows[0].cells[i].paragraphs[0].runs[0].bold = True

tcs = [
    ('TC-01', 'GPS Spoofing detection via EKF', 'MAVLink stream with lat/lon jump at t=15s', 'EKF alert within 1 packet', 'd^2 > 16.27, CRITICAL alert emitted'),
    ('TC-02', 'Command injection from rogue GCS', 'COMMAND_LONG (LAND) from system_id=99', 'CRITICAL alert R5+R7', 'Alert severity = CRITICAL, sys_id flagged'),
    ('TC-03', 'Denial-of-Service heartbeat flood', '80 HEARTBEAT pkts/sec burst', 'HIGH alert R4', 'Rate > threshold, alert in < 100ms'),
    ('TC-04', 'Replay attack detection', 'Stale-timestamp GPS packet reinjected', 'HIGH alert R6', 'Timestamp delta > 2.0s detected'),
    ('TC-05', 'Clean flight (no false positive)', '120s nominal flight, no attacks', 'No alerts generated', '0 alerts, FPR = 0%'),
    ('TC-06', 'Combined GPS spoof + Command injection', 'Simultaneous dual-vector attack', 'Both CRITICAL alerts', 'Both detection engines fire'),
]
for i, row_data in enumerate(tcs, start=1):
    for j, val in enumerate(row_data):
        tc_table.rows[i].cells[j].text = val

doc.save('Stage1_Report.docx')
doc.save('docs/Stage1_Report.docx')
print("DOCX created with user banners successfully.")
