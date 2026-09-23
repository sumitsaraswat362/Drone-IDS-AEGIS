import yaml
import argparse
import sys
from src.core.ids import AEGIS

def main():
    parser = argparse.ArgumentParser(description="AEGIS Drone IDS")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML")
    parser.add_argument("--out", default="logs", help="Output directory")
    args = parser.parse_args()

    try:
        with open(args.scenario, 'r') as f:
            scenario = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading scenario: {e}")
        sys.exit(1)

    print(f"=== AEGIS Drone IDS ===")
    print(f"Loading scenario: {scenario.get('name')}")
    print(f"Duration: {scenario.get('duration_s')}s")
    print("=======================\n")

    aegis = AEGIS(scenario=scenario, out_dir=args.out)
    report = aegis.run()

    print("\n=== Detection Report ===")
    print(f"Total Packets:    {report['total_packets']}")
    print(f"Total Alerts:     {report['total_alerts']} (Rules: {report['rule_alerts']}, ML: {report['ml_alerts']})")
    print(f"Precision:        {report['precision']:.2%}")
    print(f"Recall:           {report['recall']:.2%}")
    print(f"F1 Score:         {report['f1_score']:.3f}")
    print(f"False Pos Rate:   {report['false_positive_rate']:.2%}")
    print(f"Avg Latency:      {report['avg_detection_latency_s']}s")
    
    print("\nPer-Attack Breakdown:")
    for atk, stats in report['per_attack_type'].items():
        print(f"  - {atk}: {stats['detection_rate_pct']}% detected ({stats['detected']}/{stats['total_malicious_pkts']})")
    
    print("\nLog Integrity:")
    print(f"  Chain Hash: {report['chain_integrity_hash']}")
    print("========================\n")

if __name__ == "__main__":
    main()
