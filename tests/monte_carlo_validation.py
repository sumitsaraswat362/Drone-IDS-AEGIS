"""
AEGIS Drone IDS — Monte Carlo Validation Suite (MULTIPROCESSING VERSION)
Multi-seed, multi-scenario stress-test across 600 simulation runs.
Produces a statistically rigorous validation report with per-attack metrics.
"""
import json
import os
import sys
import time
import csv
import statistics
import concurrent.futures
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.ids import AEGIS

# ── Test Configurations ──────────────────────────────────────────────────────
SCENARIOS = [
    {
        "name": "GPS Spoofing Attack",
        "duration_s": 60,
        "attacks": [{"type": "gps_spoof", "start_s": 15.0, "end_s": 50.0, "params": {"intensity": 0.9}}]
    },
    {
        "name": "Command Injection Attack",
        "duration_s": 60,
        "attacks": [{"type": "cmd_inject", "start_s": 10.0, "end_s": 50.0, "params": {"command_id": 21}}]
    },
    {
        "name": "Denial-of-Service Flood",
        "duration_s": 60,
        "attacks": [{"type": "dos", "start_s": 10.0, "end_s": 50.0, "params": {"burst_count": 60}}]
    },
    {
        "name": "Replay Attack",
        "duration_s": 60,
        "attacks": [{"type": "replay", "start_s": 20.0, "end_s": 55.0, "params": {}}]
    },
    {
        "name": "Combined GPS + Command Injection",
        "duration_s": 60,
        "attacks": [
            {"type": "gps_spoof", "start_s": 15.0, "end_s": 50.0, "params": {"intensity": 0.8}},
            {"type": "cmd_inject", "start_s": 20.0, "end_s": 50.0, "params": {"command_id": 21}},
        ]
    },
]

SEEDS_PER_SCENARIO = 120   # 5 scenarios × 120 seeds = 600 total runs

def _confidence_interval(data: List[float], confidence: float = 0.95):
    n = len(data)
    if n < 2:
        m = data[0] if data else 0
        return m, m, m
    m   = statistics.mean(data)
    std = statistics.stdev(data)
    t   = 1.96
    margin = t * std / (n ** 0.5)
    return m, m - margin, m + margin

def _run_single_scenario(args):
    scenario, seed, out_dir = args
    run_scenario = dict(scenario)
    run_scenario["seed"] = seed
    
    aegis = AEGIS(
        scenario   = run_scenario,
        out_dir    = os.path.join(out_dir, "raw"),
        session_id = f"mc_{scenario['name'].replace(' ', '_').lower()}_{seed}",
    )
    report = aegis.run()
    return {
        "scenario": scenario["name"],
        "seed":     seed,
        **{k: report[k] for k in ["precision", "recall", "f1_score",
                                   "false_positive_rate", "avg_detection_latency_s",
                                   "true_positives", "false_positives",
                                   "false_negatives", "true_negatives"]},
    }

def run_validation(out_dir: str = "logs/validation"):
    os.makedirs(out_dir, exist_ok=True)
    all_results = []
    
    tasks = []
    for scenario in SCENARIOS:
        for seed_offset in range(SEEDS_PER_SCENARIO):
            seed = seed_offset * 7 + 42
            tasks.append((scenario, seed, out_dir))
            
    total_runs = len(tasks)
    run_count = 0
    t0 = time.time()

    print(f"\n{'='*65}")
    print(f"  AEGIS MULTIPROCESSING MONTE CARLO SUITE")
    print(f"  {total_runs} runs across {len(SCENARIOS)} scenarios")
    print(f"{'='*65}\n")

    # Use max CPU cores to smash through the simulation instantly
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = {executor.submit(_run_single_scenario, task): task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            all_results.append(future.result())
            run_count += 1
            
            elapsed = time.time() - t0
            pct = 100 * run_count / total_runs
            # Better ETA logic focusing on recent completion rate
            eta = (elapsed / run_count) * (total_runs - run_count) 
            print(f"\r  [{run_count:>3}/{total_runs}] {pct:5.1f}%  ETA: {eta:.0f}s (Processing across all CPU cores)  ", end="", flush=True)

    print(f"\n\n  Completed {total_runs} runs in {time.time() - t0:.1f}s\n")

    # Group results
    grouped = {s["name"]: [] for s in SCENARIOS}
    for r in all_results:
        grouped[r["scenario"]].append(r)
        
    scenario_summary = {}
    for name, results in grouped.items():
        prec_list = [r["precision"] for r in results]
        rec_list = [r["recall"] for r in results]
        f1_list = [r["f1_score"] for r in results]
        fpr_list = [r["false_positive_rate"] for r in results]
        lat_list = [r["avg_detection_latency_s"] for r in results if r["avg_detection_latency_s"] > 0]
        
        prec_m, prec_lo, prec_hi = _confidence_interval(prec_list)
        rec_m, rec_lo, rec_hi = _confidence_interval(rec_list)
        f1_m, f1_lo, f1_hi = _confidence_interval(f1_list)
        fpr_m, fpr_lo, fpr_hi = _confidence_interval(fpr_list)
        lat_m = statistics.mean(lat_list) if lat_list else 0.0
        
        scenario_summary[name] = {
            "n_runs":              len(results),
            "precision_mean":     round(prec_m, 4),
            "precision_95ci":     (round(prec_lo, 4), round(prec_hi, 4)),
            "recall_mean":        round(rec_m, 4),
            "recall_95ci":        (round(rec_lo, 4), round(rec_hi, 4)),
            "f1_mean":            round(f1_m, 4),
            "f1_95ci":            (round(f1_lo, 4), round(f1_hi, 4)),
            "fpr_mean":           round(fpr_m, 4),
            "fpr_95ci":           (round(fpr_lo, 4), round(fpr_hi, 4)),
            "avg_latency_s":      round(lat_m, 4),
        }

    # Write CSV
    csv_path = os.path.join(out_dir, "mc_raw_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
        writer.writeheader()
        writer.writerows(all_results)

    # Write summary JSON
    summary = {
        "total_runs":         total_runs,
        "seeds_per_scenario": SEEDS_PER_SCENARIO,
        "n_scenarios":        len(SCENARIOS),
        "wall_time_s":        round(time.time() - t0, 1),
        "per_scenario":       scenario_summary,
    }
    summary_path = os.path.join(out_dir, "mc_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    _print_table(scenario_summary)
    return summary

def _print_table(summary: dict):
    SEP = "─" * 95
    print(f"\n{SEP}")
    print(f"  {'SCENARIO':<38} {'PREC':<12} {'RECALL':<12} {'F1':<10} {'FPR':<12} {'LAT(s)'}")
    print(SEP)
    for name, s in summary.items():
        p = f"{s['precision_mean']:.3f} [{s['precision_95ci'][0]:.3f},{s['precision_95ci'][1]:.3f}]"
        r = f"{s['recall_mean']:.3f} [{s['recall_95ci'][0]:.3f},{s['recall_95ci'][1]:.3f}]"
        f = f"{s['f1_mean']:.3f}"
        fpr = f"{s['fpr_mean']:.3f}"
        print(f"  {name:<38} {p:<22} {r:<22} {f:<10} {fpr:<12} {s['avg_latency_s']:.3f}")
    print(SEP)

if __name__ == "__main__":
    run_validation()
