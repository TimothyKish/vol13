#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# sidecar_period.py  --  live status monitor for the PERIOD engine.
#
# Polls the heartbeat JSON the pipeline writes and renders a terminal dashboard.
# Upgraded to reduce "dead air": the pipeline now beats from INSIDE the annulus
# and scan loops, so the Stage line moves continuously even during one big lake.
# The sidecar also detects STALENESS -- if the heartbeat stops advancing it says
# so, rather than showing a frozen bar that looks like a hang.
#
# Usage:  python engine1d_period/sidecar_period.py
# ==============================================================================
import json, time, sys
from pathlib import Path

HEARTBEAT = Path("lakes1d_period/unified/period_heartbeat.json")
STALE_AFTER = 15   # seconds without the action string changing -> flag it

def fmt(s):
    s = int(max(0, s)); m, s = divmod(s, 60); h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"

def clear():
    sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()

def main():
    print("Waiting for Period Engine heartbeat...")
    last_action = None
    last_change = time.time()
    spin = "|/-\\"
    tick = 0
    while True:
        try:
            if HEARTBEAT.exists():
                d = json.loads(HEARTBEAT.read_text())
                pct = float(d.get("progress_pct", 0))
                action = d.get("current_action", "?")
                now = time.time()
                if action != last_action:
                    last_action = action; last_change = now
                stale = (now - last_change) > STALE_AFTER
                tick = (tick + 1) % len(spin)
                clear()
                print("=" * 62)
                print(" KISHLATTICE PERIOD SIDECAR ".center(62, "~"))
                print("=" * 62)
                print(f" Time    : {d.get('timestamp_utc')}")
                bar = "#" * int(pct//2) + "." * (50 - int(pct//2))
                print(f" Progress: [{bar}] {pct:.1f}%")
                print(f" Lakes   : {d.get('completed')} / {d.get('total')}")
                print(f" ETA     : {fmt(d.get('eta_seconds', 0))}")
                if stale:
                    print(f" Stage   : {action}")
                    print(f"           (no update for {int(now-last_change)}s -- "
                          f"a heavy lake or a large annulus; working, not hung)")
                else:
                    print(f" Stage   : {spin[tick]} {action}")
                print("=" * 62)
        except (json.JSONDecodeError, IOError):
            pass  # mid-write; retry
        time.sleep(1)

if __name__ == "__main__":
    main()
