# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC.
# FOUNDER: Timothy John Kish
#
# LICENSE & TERMS OF USE:
# This software, including the 16/pi kinematic framework and scalarization 
# engines, is open and available for scientific testing, empirical validation, 
# and academic peer review. 
#
# ATTRIBUTION REQUIREMENT:
# Any publication, derivative code, dataset generation, or public distribution 
# relying on this framework must explicitly cite the "KishLattice 16/pi Initiative" 
# and credit Timothy John Kish. 
#
# Commercial utilization, proprietary harvesting, or uncredited reproduction 
# is strictly prohibited without explicit written permission.
# ==============================================================================
import json
import time
import sys
from pathlib import Path

HEARTBEAT_PATH = Path("lakes/unified/lattice_heartbeat.json")

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"

def clear_console():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def main():
    print("Waiting for Lattice Engine Heartbeat...")
    while True:
        try:
            if HEARTBEAT_PATH.exists():
                with open(HEARTBEAT_PATH, 'r') as f:
                    data = json.load(f)
                
                pct = data.get('progress_pct', 0)
                eta = data.get('eta_seconds', 0)
                current = data.get('current_action', 'Unknown')
                
                # Terminal UI
                clear_console()
                print("=" * 60)
                print(" KISHLATTICE SIDECAR MONITOR ".center(60, "x"))
                print("=" * 60)
                print(f" Timestamp: {data.get('timestamp_utc')}")
                print(f" Progress:  [{'#' * int(pct // 2)}{'.' * (50 - int(pct // 2))}] {pct}%")
                print(f" Tasks:     {data.get('completed')} / {data.get('total')}")
                print(f" ETA:       {format_time(eta)}")
                print(f" Crunching: {current}")
                print("=" * 60)
            
        except (json.JSONDecodeError, IOError):
            # Happens if we read exactly while the engine is writing. Just ignore and retry.
            pass
            
        time.sleep(1)

if __name__ == "__main__":
    main()