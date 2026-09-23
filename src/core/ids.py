"""
AEGIS Drone IDS — Core Orchestrator
Ties together the simulator, rule engine, anomaly detector, and logger
into a single pipeline. Outputs a final JSON report.
"""
import json
import os
import time
from collections import defaultdict
from typing import Optional

from ..simulator.mavlink_simulator import MAVLinkSimulator
from ..simulator.attack_injector import AttackInjector
from ..detection.rule_engine import RuleEngine
from ..detection.anomaly_detector import AnomalyDetector
from .logger import ChainLogger


class AEGIS:
    """
    AEGIS: Autonomous Embedded Guardian for Intrusion in Swarms.
    Main IDS orchestrator.

    Pipeline:
      1. Run a short clean simulation to train the Isolation Forest baseline.
      2. Stream live packets (with attacks injected) through:
         a. RuleEngine  → deterministic signature matching
         b. AnomalyDetector → ML-based novelty scoring
      3. Log all alerts to a tamper-evident ChainLogger.
      4. Generate a final forensic report.
    """

    def __init__(self, scenario: dict, out_dir: str = "logs",
                 session_id: Optional[str] = None):
        self.scenario   = scenario
        self.out_dir    = out_dir
        self.session_id = session_id or f"aegis_{int(time.time())}"
        os.makedirs(out_dir, exist_ok=True)

        self.rule_engine      = RuleEngine(gcs_system_id=255)
        self.anomaly_detector = AnomalyDetector(contamination=0.05, random_state=42)
        self.logger           = ChainLogger(
            log_path   = os.path.join(out_dir, f"{self.session_id}_events.jsonl"),
            session_id = self.session_id,
        )

        # Metrics
        self._total_pkts   = 0
        self._rule_alerts  = 0
        self._ml_alerts    = 0
        self._tp           = 0   # True positives (attack pkt → alert fired)
        self._fp           = 0   # False positives (clean pkt → alert fired)
        self._fn           = 0   # False negatives (attack pkt → no alert)
        self._tn           = 0   # True negatives
        self._attack_counts: defaultdict = defaultdict(int)
        self._detected_attacks: defaultdict = defaultdict(int)
        self._alert_latencies = []   # seconds from attack start to first detection

    # ── Phase 1: Train on clean baseline ────────────────────────────────────
    def _train_baseline(self, duration_s: float = 30.0, seed: int = 0) -> None:
        """Run a short clean simulation and train the Isolation Forest."""
        clean_sim = MAVLinkSimulator(duration_s=duration_s, seed=seed + 999)
        clean_pkts = list(clean_sim.stream())
        self.anomaly_detector.feed_normal(clean_pkts)
        self.anomaly_detector.train()

    # ── Phase 2: Live detection ──────────────────────────────────────────────
    def run(self) -> dict:
        """Execute the full IDS pipeline and return a final report dict."""
        print(f"[AEGIS] Training baseline on 30s of clean traffic…")
        self._train_baseline(duration_s=30.0, seed=self.scenario.get('seed', 42))
        print(f"[AEGIS] Baseline trained. Starting live detection…")

        injector = AttackInjector(scenario=self.scenario,
                                   seed=self.scenario.get('seed', 42))

        attack_start_times = {
            atk['type']: atk['start_s']
            for atk in self.scenario.get('attacks', [])
        }
        first_detection_times: dict = {}

        for pkt in injector.stream():
            self._total_pkts += 1

            # Count ground-truth attacks
            if pkt.is_attack and pkt.attack_type:
                self._attack_counts[pkt.attack_type] += 1

            # ── Rule engine ──────────────────────────────────────────────────
            rule_alert = self.rule_engine.process(pkt)
            if rule_alert:
                self._rule_alerts += 1
                rule_alert['detector'] = 'RULE_ENGINE'
                self.logger.log_alert(rule_alert)
                self._update_confusion(pkt, detected=True)
                self._track_latency(pkt, rule_alert, attack_start_times,
                                     first_detection_times)

            # ── Anomaly detector ─────────────────────────────────────────────
            ml_alert = self.anomaly_detector.score_packet(pkt)
            if ml_alert and not rule_alert:   # Only escalate if rules missed it
                self._ml_alerts += 1
                ml_alert['detector'] = 'ISOLATION_FOREST'
                self.logger.log_alert(ml_alert)
                self._update_confusion(pkt, detected=True)
                self._track_latency(pkt, ml_alert, attack_start_times,
                                     first_detection_times)

            # No alert
            if not rule_alert and not ml_alert:
                self._update_confusion(pkt, detected=False)

        final_hash = self.logger.close()
        report     = self._build_report(final_hash)
        report_path = os.path.join(self.out_dir, f"{self.session_id}_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[AEGIS] Report saved → {report_path}")
        return report

    def _update_confusion(self, pkt, detected: bool) -> None:
        if pkt.is_attack and detected:
            self._tp += 1
            if pkt.attack_type:
                self._detected_attacks[pkt.attack_type] += 1
        elif pkt.is_attack and not detected:
            self._fn += 1
        elif not pkt.is_attack and detected:
            self._fp += 1
        else:
            self._tn += 1

    def _track_latency(self, pkt, alert, attack_starts, first_detections):
        atype = pkt.attack_type or alert.get('rule', 'UNKNOWN')
        if atype not in first_detections and atype in attack_starts:
            latency = pkt.timestamp_s - attack_starts[atype]
            if latency >= 0:
                first_detections[atype] = latency
                self._alert_latencies.append(latency)

    def _build_report(self, chain_hash: str) -> dict:
        total_attacks = sum(self._attack_counts.values())
        precision = self._tp / max(self._tp + self._fp, 1)
        recall    = self._tp / max(self._tp + self._fn, 1)
        f1        = 2 * precision * recall / max(precision + recall, 1e-9)
        fpr       = self._fp / max(self._fp + self._tn, 1)
        avg_lat   = sum(self._alert_latencies) / max(len(self._alert_latencies), 1)

        per_attack = {}
        for atype, count in self._attack_counts.items():
            detected = self._detected_attacks.get(atype, 0)
            per_attack[atype] = {
                "total_malicious_pkts": count,
                "detected":             detected,
                "detection_rate_pct":   round(100 * detected / max(count, 1), 2),
            }

        return {
            "session_id":         self.session_id,
            "scenario":           self.scenario.get("name", "unknown"),
            "total_packets":      self._total_pkts,
            "total_alerts":       self._rule_alerts + self._ml_alerts,
            "rule_alerts":        self._rule_alerts,
            "ml_alerts":          self._ml_alerts,
            "true_positives":     self._tp,
            "false_positives":    self._fp,
            "false_negatives":    self._fn,
            "true_negatives":     self._tn,
            "precision":          round(precision, 4),
            "recall":             round(recall, 4),
            "f1_score":           round(f1, 4),
            "false_positive_rate":round(fpr, 4),
            "avg_detection_latency_s": round(avg_lat, 3),
            "per_attack_type":    per_attack,
            "chain_integrity_hash": chain_hash,
        }
