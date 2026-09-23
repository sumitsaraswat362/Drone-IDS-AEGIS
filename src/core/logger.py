"""
AEGIS Drone IDS — Cryptographic Event Logger
Maintains a tamper-evident, chain-of-custody log of all alerts and packets
using SHA-256 chaining (each entry hashes the previous entry's hash).
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


class ChainLogger:
    """
    Write-once, append-only log with SHA-256 hash chaining.
    Each log entry contains:
      - sequence number
      - UTC timestamp
      - event type and payload
      - sha256 of this entry's content
      - sha256 of the PREVIOUS entry (chain link)

    This makes post-hoc tampering detectable: if any entry is modified,
    all subsequent chain hashes become invalid.
    """

    def __init__(self, log_path: str = "logs/aegis_events.jsonl",
                 session_id: Optional[str] = None):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_path   = log_path
        self.session_id = session_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._seq       = 0
        self._prev_hash = "GENESIS"   # Anchor hash for the first entry
        self._fh        = open(log_path, "a", encoding="utf-8")

        # Write session start marker
        self._write_entry("SESSION_START", {
            "session_id": self.session_id,
            "aegis_version": "1.0.0",
        })

    def _hash_entry(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _write_entry(self, event_type: str, payload: dict) -> dict:
        entry_content = json.dumps({
            "seq":          self._seq,
            "utc":          datetime.now(timezone.utc).isoformat(),
            "session_id":   self.session_id,
            "event_type":   event_type,
            "payload":      payload,
            "prev_hash":    self._prev_hash,
        }, separators=(",", ":"))

        entry_hash = self._hash_entry(entry_content)

        record = json.loads(entry_content)
        record["entry_hash"] = entry_hash

        line = json.dumps(record, separators=(",", ":"))
        self._fh.write(line + "\n")
        self._fh.flush()

        self._prev_hash = entry_hash
        self._seq += 1
        return record

    def log_alert(self, alert: dict) -> dict:
        """Log a detection alert."""
        return self._write_entry("ALERT", alert)

    def log_packet(self, pkt_dict: dict) -> dict:
        """Log a raw packet (used for evidence preservation)."""
        return self._write_entry("PACKET", pkt_dict)

    def log_stats(self, stats: dict) -> dict:
        """Log periodic statistics."""
        return self._write_entry("STATS", stats)

    def close(self) -> str:
        """Write session end marker and return final chain hash."""
        final = self._write_entry("SESSION_END", {
            "session_id":   self.session_id,
            "total_entries": self._seq,
        })
        self._fh.close()
        return final["entry_hash"]

    @staticmethod
    def verify_chain(log_path: str) -> dict:
        """
        Verify integrity of an existing log file.
        Returns: {valid: bool, broken_at_seq: int or None, total: int}
        """
        prev_hash = "GENESIS"
        total = 0
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line.strip())
                entry_hash = record.pop("entry_hash")
                # Recompute hash of content without entry_hash field
                content = json.dumps(record, separators=(",", ":"))
                expected = hashlib.sha256(content.encode()).hexdigest()
                if expected != entry_hash:
                    return {"valid": False, "broken_at_seq": record["seq"], "total": total}
                if record["payload"].get("prev_hash", record.get("prev_hash")) != prev_hash:
                    if total > 0:   # Skip genesis check
                        return {"valid": False, "broken_at_seq": record["seq"], "total": total}
                prev_hash = entry_hash
                total += 1
        return {"valid": True, "broken_at_seq": None, "total": total}
