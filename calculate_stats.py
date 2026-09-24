import os, json, glob, statistics
from collections import defaultdict
from typing import List, Dict

SCENARIOS = ["GPS Spoofing Attack", "Command Injection Attack", "Denial-of-Service Flood", "Replay Attack", "Combined GPS + Command Injection"]

def _confidence_interval(data: List[float]):
    n = len(data)
    if n < 2: return 0,0,0
    m = statistics.mean(data)
    std = statistics.stdev(data)
    t = 1.96
    margin = t * std / (n ** 0.5)
    return m, m - margin, m + margin

def run():
    files = glob.glob("logs/validation/raw/*_report.json")
    if not files:
        print("No files found!")
        return

    grouped = defaultdict(list)
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
            scen_name = data["scenario"]
            grouped[scen_name].append(data)
            
    summary = {}
    for name, results in grouped.items():
        if len(results) < 5: continue
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
        
        summary[name] = {
            "n_runs": len(results),
            "precision_mean": round(prec_m, 4),
            "precision_95ci": (round(prec_lo, 4), round(prec_hi, 4)),
            "recall_mean": round(rec_m, 4),
            "recall_95ci": (round(rec_lo, 4), round(rec_hi, 4)),
            "f1_mean": round(f1_m, 4),
            "f1_95ci": (round(f1_lo, 4), round(f1_hi, 4)),
            "fpr_mean": round(fpr_m, 4),
            "fpr_95ci": (round(fpr_lo, 4), round(fpr_hi, 4)),
            "avg_latency_s": round(lat_m, 4),
        }
    
    print(json.dumps(summary, indent=2))
    
run()
