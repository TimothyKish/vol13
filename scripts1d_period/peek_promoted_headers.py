#!/usr/bin/env python3
# ==============================================================================
# peek_promoted_headers.py
# Scans the first record of every promoted lake to inventory the available 
# physical fields and metadata keys for targeted multi-attribute extraction.
# ==============================================================================
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"

def main():
    if not IN_DIR.exists():
        print(f"[!] Directory not found: {IN_DIR}")
        return

    files = sorted(list(IN_DIR.glob("*_promoted.jsonl")))
    print(f"[*] Scanning schemas for {len(files)} promoted lakes...\n")

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Find the first non-empty line
                first_line = ""
                for line in f:
                    if line.strip():
                        first_line = line
                        break
                        
                if not first_line:
                    print(f"[{file_path.name}] - EMPTY FILE")
                    continue
                    
                rec = json.loads(first_line)
                
                # Extract keys
                payload_keys = list(rec.get("_raw_payload", {}).keys())
                meta_keys = list(rec.get("meta", {}).keys())
                top_keys = [k for k in rec.keys() if k not in ["_raw_payload", "meta", "entity_id", "domain", "lake_id"]]
                
                print(f"=== {file_path.name} ===")
                if top_keys:
                    print(f"  Top-level : {top_keys}")
                if payload_keys:
                    print(f"  Payload   : {payload_keys}")
                if meta_keys:
                    print(f"  Meta      : {meta_keys}")
                print()
                
        except Exception as e:
            print(f"[{file_path.name}] Error reading: {e}")

if __name__ == "__main__":
    main()