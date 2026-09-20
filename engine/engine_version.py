"""
engine_version.py
KishLattice Geometric Harmonic Spectroscopy — Engine Fingerprint Tool

Computes a 192-character audit fingerprint from the six files that fully
determine pipeline output:

  Position   File
  --------   ----
  [0:32]     engine/scalarize.py
  [32:64]    engine/unify.py
  [64:96]    engine/build_chaos_nulls.py
  [96:128]   engine/build_pinch_table.py
  [128:160]  configs/scalarize.json
  [160:192]  configs/volumes.json

Each segment is the MD5 hexdigest (32 hex characters) of that file's bytes.
The concatenated 192-char string uniquely identifies the exact engine state
that produced any given pipeline output.

Platform note:
  MD5 is identical on Windows and Linux provided line endings are normalised.
  Enforce LF endings via .gitattributes:
    *.py    text eol=lf
    *.json  text eol=lf

Backward compatibility:
  128-char strings (scripts only, pre-Vol10) are accepted by parse/verify.
  160-char strings (scripts + scalarize.json, pre-volumes fingerprint) likewise.

Usage:
  python engine/engine_version.py                   # print current fingerprint
  python engine/engine_version.py --parse  <string> # decompose a fingerprint
  python engine/engine_version.py --verify <string> # verify against current files
  python engine/engine_version.py --write  <file>   # write fingerprint to file

Author: Mondy Aurora Kish / Timothy John Kish
Volume: 10 (May 2026)
"""
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

import hashlib
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# File slot definitions — ORDER IS CANONICAL AND MUST NOT CHANGE
# ---------------------------------------------------------------------------

SLOT_DEFINITIONS = [
    ('scalarize_py',          'engine',  'scalarize.py'),
    ('unify_py',              'engine',  'unify.py'),
    ('build_chaos_nulls_py',  'engine',  'build_chaos_nulls.py'),
    ('build_pinch_table_py',  'engine',  'build_pinch_table.py'),
    ('scalarize_json',        'configs', 'scalarize.json'),
    ('volumes_json',          'configs', 'volumes.json'),
]

VALID_LENGTHS = {128, 160, 192}
SEGMENT_SIZE  = 32   # MD5 hexdigest length


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def _md5_file(filepath: Path) -> str:
    """
    Compute MD5 hexdigest of a file's raw bytes.
    Reads in 8KB chunks to handle large files without memory issues.
    Identical output on Windows and Linux when line endings are LF.
    """
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _resolve_base(base_dir=None) -> Path:
    """Resolve the vol root directory (parent of engine/)."""
    if base_dir is not None:
        return Path(base_dir)
    # When called from engine/, go up one level to vol root
    return Path(__file__).resolve().parent.parent


def compute_engine_version(base_dir=None) -> str:
    """
    Compute and return the 192-character engine fingerprint.

    Raises FileNotFoundError if any of the six required files is missing.
    This is intentional: a partial engine state must not produce a fingerprint.
    """
    base = _resolve_base(base_dir)
    segments = []

    for slot_name, subfolder, filename in SLOT_DEFINITIONS:
        path = base / subfolder / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Engine fingerprint requires '{path}' but it does not exist.\n"
                f"Slot: {slot_name}\n"
                f"Ensure all six engine/config files are present before running."
            )
        segments.append(_md5_file(path))

    version_string = ''.join(segments)
    assert len(version_string) == 192, f"Internal error: expected 192 chars, got {len(version_string)}"
    return version_string


def parse_engine_version(version_string: str) -> dict:
    """
    Decompose a version string into named slot dictionaries.

    Accepts 128-char (legacy: scripts only),
            160-char (legacy: scripts + scalarize.json),
            192-char (current: all six files).

    Returns dict mapping slot name -> 32-char MD5 hex string.
    """
    n = len(version_string)
    if n not in VALID_LENGTHS:
        raise ValueError(
            f"Invalid version string length: {n}. "
            f"Valid lengths: {sorted(VALID_LENGTHS)}"
        )

    result = {}
    n_slots = n // SEGMENT_SIZE
    for i, (slot_name, _, _) in enumerate(SLOT_DEFINITIONS[:n_slots]):
        start = i * SEGMENT_SIZE
        result[slot_name] = version_string[start:start + SEGMENT_SIZE]

    return result


def verify_engine_version(reported_version: str, base_dir=None) -> tuple:
    """
    Compare a reported version string against the current files.

    Returns:
        (match: bool, changed_components: list[str])

    If match is True, changed_components is empty.
    If match is False, changed_components names the slots that differ.

    Note: comparison is limited to the length of reported_version,
    enabling backward-compatible verification of 128 and 160-char strings.
    """
    n = len(reported_version)
    if n not in VALID_LENGTHS:
        raise ValueError(f"Invalid version string length: {n}")

    current_full = compute_engine_version(base_dir)
    current_trimmed = current_full[:n]

    if current_trimmed == reported_version:
        return True, []

    # Identify which slots changed
    rep_slots = parse_engine_version(reported_version)
    cur_slots = parse_engine_version(current_trimmed)
    changed = [k for k in rep_slots if rep_slots[k] != cur_slots.get(k)]

    return False, changed


def engine_version_metadata(base_dir=None) -> dict:
    """
    Return a metadata dict suitable for embedding in pipeline output files.

    Example output:
      {
        "engine_version": "a3f2...b309...",
        "engine_version_parsed": {
            "scalarize_py": "a3f2...",
            ...
        },
        "generated_utc": "2026-05-06T14:32:00Z"
      }
    """
    version = compute_engine_version(base_dir)
    return {
        'engine_version':        version,
        'engine_version_parsed': parse_engine_version(version),
        'generated_utc':         datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_parsed(version_string: str):
    parsed = parse_engine_version(version_string)
    slot_labels = {slot: f"{sub}/{fn}" for slot, sub, fn in SLOT_DEFINITIONS}
    for slot_name, md5_hex in parsed.items():
        label = slot_labels.get(slot_name, slot_name)
        print(f"  {slot_name:<30} {md5_hex}   ({label})")


def main():
    parser = argparse.ArgumentParser(
        description='KishLattice engine fingerprint tool — Vol 10',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python engine/engine_version.py
      Print the current 192-char fingerprint and its components.

  python engine/engine_version.py --parse a3f2...b309
      Decompose a reported fingerprint into named slot hashes.

  python engine/engine_version.py --verify a3f2...b309
      Verify current files match the reported fingerprint.
      Exit code 0 = match, exit code 1 = mismatch.

  python engine/engine_version.py --write engine_baseline_v10.txt
      Write the current fingerprint and timestamp to a file.
        """
    )
    parser.add_argument(
        '--verify', metavar='VERSION_STRING',
        help='Verify a reported version string against current files'
    )
    parser.add_argument(
        '--parse', metavar='VERSION_STRING',
        help='Decompose a version string into named components'
    )
    parser.add_argument(
        '--write', metavar='OUTPUT_FILE',
        help='Write current fingerprint and metadata to a file'
    )
    parser.add_argument(
        '--base', metavar='DIR',
        help='Override vol root directory (default: parent of engine/)'
    )

    args = parser.parse_args()

    try:
        if args.verify:
            match, changed = verify_engine_version(args.verify, args.base)
            if match:
                print("VERIFIED: Current engine matches the reported version string.")
                print()
                _print_parsed(args.verify)
                sys.exit(0)
            else:
                print("MISMATCH: The following components differ from the reported version:")
                for c in changed:
                    print(f"  {c}")
                print()
                print("Reported version:")
                _print_parsed(args.verify)
                print()
                current = compute_engine_version(args.base)[:len(args.verify)]
                print("Current version:")
                _print_parsed(current)
                sys.exit(1)

        elif args.parse:
            print(f"Version string ({len(args.parse)} chars):")
            _print_parsed(args.parse)

        elif args.write:
            meta = engine_version_metadata(args.base)
            out = Path(args.write)
            out.write_text(
                f"engine_version: {meta['engine_version']}\n"
                f"generated_utc:  {meta['generated_utc']}\n\n"
                f"Components:\n"
                + '\n'.join(
                    f"  {k:<30} {v}"
                    for k, v in meta['engine_version_parsed'].items()
                ) + '\n',
                encoding='utf-8'
            )
            print(f"Fingerprint written to: {out}")
            print(f"  {meta['engine_version']}")

        else:
            # Default: print fingerprint and components
            version = compute_engine_version(args.base)
            print(version)
            print()
            _print_parsed(version)

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()