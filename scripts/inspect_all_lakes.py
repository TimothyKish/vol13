# ==============================================================================
# SCRIPT: scripts/inspect_all_lakes.py
# PURPOSE: Utility to automatically scan and print the data payload schema 
#          for every promoted lake in the directory.
# ==============================================================================
import json
from pathlib import Path

def peek_at_lake(file_path):
    print(f"--- Peeking at: {file_path.name} ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if not first_line:
                print("  -> File is empty.\n")
                return
            
            try:
                data = json.loads(first_line)
                
                # Filter standard KishLattice routing keys to highlight the physical data payloads
                standard_keys = {"entity_id", "id", "domain", "volume", "lake_id", "geometry_payload", "meta", "_raw_payload", "scalar_klc", "scalar_kls"}
                
                found_routing = [k for k in standard_keys if k in data]
                data_keys = [k for k in data.keys() if k not in standard_keys]
                
                print(f"  Standard Keys : {', '.join(found_routing)}")
                
                if data_keys:
                    print("  Unique Data Fields (Payload):")
                    for key in data_keys:
                        val = data[key]
                        # Truncate long values so the terminal doesn't get flooded
                        val_str = str(val)[:60] + "..." if len(str(val)) > 60 else str(val)
                        print(f"    -> '{key}': {val_str}")
                else:
                    print("  -> NO UNIQUE DATA FIELDS FOUND (Only standard routing keys).")
                    
            except json.JSONDecodeError:
                print("  -> Error: First line is not valid JSON.")
    except Exception as e:
        print(f"  -> Error reading file: {e}")
    print("-" * 60)

if __name__ == "__main__":
    # Dynamically locate the inputs_promoted directory
    current_dir = Path.cwd()
    promoted_dir = current_dir / "lakes" / "inputs_promoted"
    
    # Fallback if run from inside the scripts folder directly
    if not promoted_dir.exists():
        promoted_dir = Path(__file__).resolve().parent.parent / "lakes" / "inputs_promoted"
        
    if not promoted_dir.exists():
        print(f"[ERROR] Could not find the lakes/inputs_promoted directory.")
        print(f"Looked in: {promoted_dir}")
        exit(1)

    print("=" * 60)
    print(f" INSPECTING ALL PROMOTED LAKES IN:\n {promoted_dir.name}")
    print("=" * 60 + "\n")

    # Find all promoted jsonl files
    jsonl_files = list(promoted_dir.glob("*_promoted.jsonl"))
    
    if not jsonl_files:
        print("No *_promoted.jsonl files found in the directory.")
    else:
        print(f"Found {len(jsonl_files)} lakes to inspect.\n")
        # Sort alphabetically for a clean read
        for file_path in sorted(jsonl_files):
            peek_at_lake(file_path)
        
    print(f"\n[DONE] Inspected {len(jsonl_files)} lakes.")