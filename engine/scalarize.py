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
# SCRIPT: scalarize.py
# TARGET: Apply domain-native scalarization to all promoted lakes
# AUTHORS: Timothy John Kish
# AUDIT STATUS: Lyra-verified 2026-05-15 (Streaming memory-safe rewrite + Heartbeat)
#
# UPGRADE Vol 11.1: Rule 1.5 — Config-Driven Scalar Dispatch
#   Reads scalarize.json at startup (cached once). All domains defined in
#   scalarize.json now receive correct scalar computation even if no named
#   handler exists in the dispatch table. This fixes:
#     - Broken multi-attribute lakes: k2a-k2d, h1b-h1d, g1a-g1c, galactic_mass,
#       orbital_transit, p_transit
#     - Wrongbox lakes: now run genuine wrong-projection math on real data
#       (log_volumetric, log_inverse) rather than silently returning 0.0
#   Priority: named handlers always win. Config dispatch is the new fallback
#   layer BEFORE the final (0.0, 0.0) return.
#
# UPGRADE Vol 12: Field Resolver + Dispatch Attribution
#   - resolve_field(): plain keys resolve breadth-first through nested payloads
#     (shallowest wins); explicit dotted paths supported. `is None` throughout,
#     so a stored 0.0 is a value rather than a miss. Path cached per domain.
#   - Dispatch telemetry: every record attributed to the route that produced its
#     scalar. The legacy precomputed-scalar fallback is now COUNTED and NAMED,
#     and aborts the run under KLGHS_STRICT=1 (default).
#   - scalarize_atomic_ionisation: read 'ionisation_energy_ev' (lake spelling),
#     not 'ionisation_energy_eV'. Q8 was silently on the legacy fallback.
#   No formula changed. log_standard / log_inverse / log_ratio / log_volumetric
#   are byte-for-byte identical to Vol 11.1.
#
# UPGRADE Vol 12.1: math.log(1.0 + u) -> math.log1p(u)
#   Vol 11.1 computed log(1.0 + u) directly. In float64, 1.0 + u == 1.0 exactly
#   for u <= 1.11e-16, so any such value absorbed to a scalar of exactly zero.
#   log_volumetric is worse: it forms log(1.0 + x**3), which absorbs at
#   x <= 4.81e-06 -- reached by kinematic_wrongbox, whose input velocities have
#   a measured minimum of 4.88e-13 km/s.
#   log1p is exact in that regime and identical elsewhere. This is a numerical
#   correctness fix, not a change of formula: the mathematical definition of
#   every branch is unchanged.
# ==============================================================================

#!/usr/bin/env python
import collections
import json
import math
import os
import time
from pathlib import Path
from typing import Dict, Any, Iterable

ROOT       = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"
INPUT_DIR  = ROOT / "lakes" / "inputs_promoted"
OUTPUT_DIR = ROOT / "lakes" / "unified"
HEARTBEAT_PATH = OUTPUT_DIR / "lattice_heartbeat.json"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PI    = math.pi
K_GEO = 16.0 / PI
LOG_K = math.log(K_GEO)

# ==============================================================================
# RULE 1.5: CONFIG-DRIVEN SCALAR DISPATCH
# Loads scalarize.json once at startup and caches it.
# Used as fallback layer in scalarize_record() before returning (0.0, 0.0).
# ==============================================================================

SCALARIZE_CONFIG_PATH = CONFIG_DIR / "scalarize.json"

def _load_scalarize_config():
    """Load scalarize.json once at startup. Returns domain config dict."""
    if not SCALARIZE_CONFIG_PATH.exists():
        print(f"[WARN] scalarize.json not found at {SCALARIZE_CONFIG_PATH}")
        return {}
    try:
        with open(SCALARIZE_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        domains = cfg.get("domains", {})
        print(f"[scalarize.json] Loaded config for {len(domains)} domains.")
        return domains
    except Exception as e:
        print(f"[WARN] Could not load scalarize.json: {e}")
        return {}

# Cached once at module import — not reloaded per record
_SCALARIZE_DOMAIN_CONFIG = _load_scalarize_config()


# ==============================================================================
# VOL 12: FIELD RESOLVER
# The Vol 11.1 lookup checked top-level, _raw_payload and payload only, using
# `or` chaining that treats a stored 0.0 as missing. Promoted lakes nest their
# raw values at varying depth (t2/t4 sit four levels down after repeated
# re-promotion), so configured fields were silently unresolvable.
#
# Accepts a plain key ('vdisp') or an explicit dotted path
# ('meta.val_raw_kms'). Plain keys resolve breadth-first, shallowest wins.
# All checks use `is None`: a stored 0.0 is a value, not a miss.
# ==============================================================================

MAX_RESOLVE_DEPTH = 6


def _dotted(record, path):
    cur = record
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def resolve_field(record, field):
    """Return (value, dotted_path) or (None, None)."""
    if not field:
        return (None, None)

    if "." in field:
        val = _dotted(record, field)
        return (None, None) if val is None else (val, field)

    frontier = [(record, "")]
    depth = 0
    while frontier and depth <= MAX_RESOLVE_DEPTH:
        nxt = []
        for obj, prefix in frontier:
            if not isinstance(obj, dict):
                continue
            if field in obj and obj[field] is not None:
                return (obj[field], f"{prefix}.{field}" if prefix else field)
            for k, v in obj.items():
                if isinstance(v, dict):
                    nxt.append((v, f"{prefix}.{k}" if prefix else k))
        frontier = nxt
        depth += 1
    return (None, None)


# ==============================================================================
# VOL 12: DISPATCH TELEMETRY
# Every record's scalar is attributed to the path that produced it.
#
# The failure mode this exists to expose: when named-handler and config dispatch
# both return zero, the legacy layer substitutes the lake's precomputed
# scalar_kls. The domain then reports nonzero=n and looks healthy while carrying
# a number of unverified provenance. Under KLGHS_STRICT (default on) this now
# aborts the run instead.
# ==============================================================================

STRICT_MODE = os.environ.get("KLGHS_STRICT", "1") == "1"

# Set by scalarize_from_config on every call. Distinguishes "computed a value
# that happens to be 0.0" from "failed to compute". Without this the legacy
# fallback fires on a legitimate zero -- the same bug class as `or` chaining,
# one level up.
_CONFIG_OK = False

_DISPATCH_LOG   = collections.defaultdict(collections.Counter)
_RESOLVED_PATHS = {}
_FAILURE_DETAIL = collections.defaultdict(set)


def _note(domain, route):
    _DISPATCH_LOG[domain][route] += 1


def _note_failure(domain, reason, detail):
    _FAILURE_DETAIL[domain].add(f"{reason}: {detail}")


def _note_resolution(domain, field, path):
    if domain not in _RESOLVED_PATHS:
        _RESOLVED_PATHS[domain] = (field, path)


def dispatch_report():
    """Print per-domain scalar attribution. Returns domains on legacy fallback."""
    print("\n" + "=" * 78)
    print("SCALAR DISPATCH ATTRIBUTION")
    print("=" * 78)
    print(f"  {'domain':<32}{'route':<22}{'records':>12}")
    offenders = []
    for domain in sorted(_DISPATCH_LOG):
        for route, count in _DISPATCH_LOG[domain].most_common():
            print(f"  {domain:<32}{route:<22}{count:>12,}")
            if route == "LEGACY_PRECOMPUTED":
                offenders.append(domain)

    if _RESOLVED_PATHS:
        print("\n  Resolved field paths:")
        for d, (f, p) in sorted(_RESOLVED_PATHS.items()):
            flag = "" if f == p else f"   (config asked '{f}')"
            print(f"    {d:<32} -> {p}{flag}")

    offenders = sorted(set(offenders))
    if offenders:
        print("\n" + "!" * 78)
        print("  LEGACY FALLBACK FIRED.")
        print("  These domains did NOT compute from their configured field. Their")
        print("  scalars are precomputed values carried in the lake, of unverified")
        print("  provenance. Results for these domains are not citable.")
        for d in offenders:
            print(f"    {d}")
            for detail in sorted(_FAILURE_DETAIL.get(d, [])):
                print(f"        {detail}")
        print("!" * 78)
    else:
        print("\n  No legacy fallback. Every domain computed from its configured field.")
    print("=" * 78 + "\n")
    return offenders


def scalarize_from_config(record, domain):
    """
    Rule 1.5: Config-driven scalar dispatch.

    Reads the domain entry from the cached scalarize.json config, extracts
    the specified field from the record, and applies the specified formula.

    Formula types (matching scalarize.json spec):
      log_standard:   log(1 + x/x0) / log(k_geo)   — standard positive measurement
      log_inverse:    log(1 + x0/x) / log(k_geo)   — inverse (wrong projection for wrongboxes)
      log_ratio:      log(x/x0) / log(k_geo)        — ratio without offset
      log_volumetric: log(1 + x^3) / log(k_geo)     — cubic transform (wrong projection)
      precomputed:    x                             — stored value IS the scalar (Vol 12)

    The wrongbox domains use log_volumetric or log_inverse intentionally:
      orbital_wrongbox:   period_days cubed    — geometrically wrong for a 1D period
      kinematic_wrongbox: v_perp cubed         — geometrically wrong for a 1D velocity
      stellar_wrongbox:   P0_ms inverted       — geometrically wrong for a period
      materials_wrongbox: volume log_standard  — the field itself is already 3D

    Returns (scalar_kls, scalar_klc) — both set to the same computed scalar.
    Returns (0.0, 0.0) only if domain not in config, field missing, or invalid.
    """
    global _CONFIG_OK
    _CONFIG_OK = False

    cfg = _SCALARIZE_DOMAIN_CONFIG.get(domain)
    if cfg is None:
        return (0.0, 0.0)

    field        = cfg.get("data_field") or cfg.get("field")  # FIX: config uses data_field
    formula_type = cfg.get("formula_type", "log_standard")
    x0           = float(cfg.get("x0", 1.0))

    if not field:
        return (0.0, 0.0)

    # Field extraction via the Vol 12 resolver. Cached per domain: the first
    # record establishes the path, subsequent records address it directly, so
    # the breadth-first walk runs once per domain rather than once per record.
    cached = _RESOLVED_PATHS.get(domain)
    raw_val = None
    resolved_path = None
    if cached is not None and cached[0] == field:
        raw_val = _dotted(record, cached[1])
        resolved_path = cached[1]
    if raw_val is None:
        raw_val, resolved_path = resolve_field(record, field)

    if raw_val is None:
        _note_failure(domain, "FIELD_NOT_FOUND", field)
        return (0.0, 0.0)

    _note_resolution(domain, field, resolved_path)

    try:
        x = float(raw_val)
    except (TypeError, ValueError):
        _note_failure(domain, "FIELD_NOT_NUMERIC", f"{field}={raw_val!r}")
        return (0.0, 0.0)

    # Negative values: take absolute (physical magnitudes are always positive)
    if x < 0:
        x = abs(x)

    # Apply the formula
    try:
        if formula_type == "log_standard":
            # Standard: log(1 + x/x0) / log(k_geo)
            sc = math.log1p(x / x0) / LOG_K

        elif formula_type == "log_inverse":
            # Inverse: log(1 + x0/x) / log(k_geo)
            # Used in wrongboxes: inverts a quantity that should not be inverted.
            # Will produce real non-zero scalars. Their harmonic structure (or lack
            # thereof) is the physical test.
            if x == 0:
                return (0.0, 0.0)
            sc = math.log1p(x0 / x) / LOG_K

        elif formula_type == "log_ratio":
            # Ratio: log(x/x0) / log(k_geo)
            if x <= 0 or x0 <= 0:
                return (0.0, 0.0)
            sc = math.log(x / x0) / LOG_K

        elif formula_type == "log_volumetric":
            # Volumetric (cubic): log(1 + x^3) / log(k_geo)
            # Used in wrongboxes: cubes a 1D quantity (period, velocity) to apply
            # a 3D volumetric projection. Deliberately wrong geometry.
            # Will produce real non-zero scalars. Their harmonic structure (or lack
            # thereof) is the physical test.
            x3 = x ** 3
            if not math.isfinite(x3):
                # Overflow on very large values — scale down and recompute
                sc = math.log(x) * 3.0 / LOG_K
            else:
                sc = math.log1p(x3) / LOG_K

        elif formula_type == "precomputed":
            # VOL 12: the lake's stored value IS the KLGHS scalar. Declaring
            # this in config converts what the legacy fallback did silently
            # into an auditable, signed-off choice. Requires a provenance note
            # in the domain entry stating what produced the stored scalar.
            sc = x

        else:
            # Unknown formula type — genuine fallthrough
            return (0.0, 0.0)

        if not math.isfinite(sc):
            return (0.0, 0.0)

        _CONFIG_OK = True
        return (sc, sc)

    except (ValueError, OverflowError, ZeroDivisionError):
        return (0.0, 0.0)


def load_enabled_lakes():
    """
    VOL 12: honour the 'path' key from volumes.json.

    Vol 11.1 built every input path as {lake}_promoted.jsonl by convention and
    skipped silently when the file was absent. Lakes whose promoted file does
    not follow that convention -- p_eccentricity (p_ecc_promoted.jsonl),
    p_inclination (p_incl_promoted.jsonl), p1_wrongbox (p1_wrong_promoted.jsonl)
    -- were dropped from every run without appearing in any log.

    Returns (tuple_of_lake_names, {lake: resolved_Path}).
    """
    cfg = json.load(open(CONFIG_DIR / "volumes.json", "r", encoding="utf-8"))
    names, paths = [], {}
    for n, m in cfg.get("volumes", {}).items():
        if not m.get("enabled", False):
            continue
        names.append(n)
        p = m.get("path")
        paths[n] = (ROOT / p.replace("\\", "/")) if p else (INPUT_DIR / f"{n}_promoted.jsonl")
    return tuple(names), paths

LAKES, LAKE_PATHS = load_enabled_lakes()
MODE  = "geometry"

def compute_geometry_payload(raw):
    return {"coordinates": [], "dimensionality": 0, "geometry_type": "unknown"}

# ==============================================================================
# HEARTBEAT TELEMETRY
# ==============================================================================
def write_heartbeat(pct, elapsed, total_tasks, completed_tasks, current_action):
    eta = (elapsed / max(1, completed_tasks)) * (total_tasks - completed_tasks) if completed_tasks > 0 else 0
    data = {
        "timestamp_utc": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        "progress_pct": min(100.0, max(0.0, round(pct, 2))),
        "completed": completed_tasks,
        "total": total_tasks,
        "eta_seconds": round(eta, 1),
        "current_action": current_action
    }
    try:
        with open(HEARTBEAT_PATH, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# ==============================================================================
# EXISTING HANDLERS — unchanged, read from _raw_payload (legacy Vol5-8 format)
# ==============================================================================
def scalarize_biology(record):
    payload = record.get("_raw_payload", {}) or {}
    inv = payload.get("scalar_invariant")
    return (float(inv), float(inv)) if inv is not None else (0.0, 0.0)

def scalarize_chemistry(record):
    payload = record.get("_raw_payload", {}) or {}
    inv = payload.get("scalar_invariant")
    return (float(inv), float(inv)) if inv is not None else (0.0, 0.0)

def scalarize_materials(record):
    payload = record.get("_raw_payload", {}) or {}
    inv = payload.get("lattice_deviation") or payload.get("scalar_invariant")
    return (float(inv), float(inv)) if inv is not None else (0.0, 0.0)

def scalarize_frb(record):
    payload = record.get("_raw_payload", {}) or {}
    inv = payload.get("scalar_invariant")
    return (float(inv), float(inv)) if inv is not None else (0.0, 0.0)

def scalarize_null(record):
    return 0.0, 0.0

# ==============================================================================
# NEW HANDLERS (Vol9) — read flat fields from promoted records
# ==============================================================================
def _log_scalar(val):
    """Standard: log(val + 1) / log(k_geo). Returns 0.0 if invalid."""
    try:
        fval = float(val)
        if fval < 0: fval = abs(fval)
        if not math.isfinite(fval) or fval == 0: return 0.0
        sc = math.log(fval + 1.0) / LOG_K
        return sc if math.isfinite(sc) else 0.0
    except (TypeError, ValueError):
        return 0.0

def scalarize_nuclear_binding(record):
    sc = _log_scalar(record.get("binding_energy_mev_per_A"))
    return (sc, sc)

def scalarize_nuclear_decay(record):
    """Double-log: log(log(half_life_seconds + 1) + 1) / log(k_geo)"""
    try:
        hl = float(record.get("half_life_seconds", 0))
        if hl <= 0 or not math.isfinite(hl): return (0.0, 0.0)
        inner = math.log(hl + 1.0)
        if inner <= 0: return (0.0, 0.0)
        sc = math.log(inner + 1.0) / LOG_K
        sc = sc if math.isfinite(sc) else 0.0
        return (sc, sc)
    except (TypeError, ValueError):
        return (0.0, 0.0)

def scalarize_atomic_ionisation(record):
    sc = _log_scalar(record.get("ionisation_energy_ev"))
    return (sc, sc)

def scalarize_molecular_c60(record):
    sc = _log_scalar(record.get("frequency_cm1"))
    return (sc, sc)

def scalarize_stellar_cycle(record):
    sc = _log_scalar(record.get("interval_days"))
    return (sc, sc)

def scalarize_gravitational_wave(record):
    sc = _log_scalar(record.get("f_ring_hz"))
    return (sc, sc)

def scalarize_tidal(record):
    sc = _log_scalar(record.get("interval_hours"))
    return (sc, sc)

def scalarize_cmb_anisotropy(record):
    dt = record.get("delta_T_uK")
    if dt is None:
        dl = record.get("Dl_uK2", 0)
        try:
            dl_f = float(dl)
            dt = math.sqrt(dl_f) if dl_f > 0 else 0.0
        except (TypeError, ValueError):
            dt = 0.0
    sc = _log_scalar(dt)
    return (sc, sc)

# ==============================================================================
# NEW HANDLERS (Vol10)
# ==============================================================================
def scalarize_seismic_temporal(record):
    sc = _log_scalar(record.get("interval_days"))
    return (sc, sc)

def scalarize_orbital_ttv(record):
    sc = _log_scalar(record.get("ttv_absolute_minutes"))
    return (sc, sc)

def scalarize_subnuclear_mass(record):
    sc = _log_scalar(record.get("invariant_mass_gev"))
    return (sc, sc)

def scalarize_biology_backbone(record):
    try:
        val = float(record.get("angle_degrees", 0) or 0)
        sc = _log_scalar(abs(val))
        return (sc, sc)
    except (TypeError, ValueError):
        return (0.0, 0.0)

# ==============================================================================
# DISPATCH TABLE
# Priority order:
#   1. Named domain handlers (all existing code above — unchanged)
#   2. Rule 1.5: scalarize_from_config() — config-driven fallback
#   3. Legacy scalar_kls fallback (unchanged)
#   4. Final (0.0, 0.0)
# ==============================================================================
def scalarize_record(record, lake_id):
    domain       = (record.get("domain") or "").lower()
    domain_group = domain

    if domain in ("mechanical", "behavioral", "mathematical", "cosmological_null"):
        domain_group = "null"

    _route_taken = "NAMED_HANDLER"
    _computed = None          # set by the config path; None => infer from value

    # --- Named handlers (priority 1: unchanged from original) ---
    if domain_group == "biology":
        scalar_kls, scalar_klc = scalarize_biology(record)
    elif domain_group == "chemistry":
        scalar_kls, scalar_klc = scalarize_chemistry(record)
    elif domain_group == "materials":
        scalar_kls, scalar_klc = scalarize_materials(record)
    elif domain_group in (
        "astrophysics", 
        "frb", 
        "stellar", 
        "planetary", 
        "cosmology"
    ):
        scalar_kls, scalar_klc = scalarize_frb(record)
    elif domain_group == "null":
        scalar_kls, scalar_klc = scalarize_null(record)
    elif domain_group == "nuclear_binding":
        scalar_kls, scalar_klc = scalarize_nuclear_binding(record)
    elif domain_group == "nuclear_decay":
        scalar_kls, scalar_klc = scalarize_nuclear_decay(record)
    elif domain_group == "atomic_ionisation":
        scalar_kls, scalar_klc = scalarize_atomic_ionisation(record)
    elif domain_group == "molecular_c60":
        scalar_kls, scalar_klc = scalarize_molecular_c60(record)
    elif domain_group == "stellar_cycle":
        scalar_kls, scalar_klc = scalarize_stellar_cycle(record)
    elif domain_group == "gravitational_wave":
        scalar_kls, scalar_klc = scalarize_gravitational_wave(record)
    elif domain_group in (
        "planetary_atlantic", 
        "planetary_gulf", 
        "planetary_pacific", 
        "planetary_indian"
    ):
        scalar_kls, scalar_klc = scalarize_tidal(record)
    elif domain_group == "cmb_anisotropy":
        scalar_kls, scalar_klc = scalarize_cmb_anisotropy(record)
    elif domain_group == "seismic_temporal":
        scalar_kls, scalar_klc = scalarize_seismic_temporal(record)
    elif domain_group == "orbital_ttv":
        scalar_kls, scalar_klc = scalarize_orbital_ttv(record)
    elif domain_group == "subnuclear_mass":
        scalar_kls, scalar_klc = scalarize_subnuclear_mass(record)
    elif domain_group == "biology_backbone":
        scalar_kls, scalar_klc = scalarize_biology_backbone(record)
    else:
        # --- Rule 1.5: Config-driven dispatch (priority 2) ---
        # Before returning zeros, check scalarize.json for this domain.
        # Handles all lakes defined in config without a named handler:
        #   - Multi-attribute lakes: stellar_spindown, stellar_dm, stellar_age,
        #     stellar_bfield, subnuclear_pt_lead, subnuclear_pt_sublead,
        #     subnuclear_eta, galactic_radius, galactic_sersic, galactic_mass,
        #     orbital_transit, orbital_eccentricity, orbital_inclination
        #   - Wrongbox lakes: orbital_wrongbox, kinematic_wrongbox,
        #     stellar_wrongbox, materials_wrongbox
        #     (These use log_volumetric or log_inverse — genuine wrong-projection
        #      math on real data, not silent zeros from a missing handler.)
        _route_taken = "CONFIG_DISPATCH"
        scalar_kls, scalar_klc = scalarize_from_config(record, domain_group)
        _computed = _CONFIG_OK
        # FIX: scalarize.json is keyed by lake_id; records lacking a domain
        # (e.g. electron lakes) must resolve via lake_id.
        if not _computed:
            scalar_kls, scalar_klc = scalarize_from_config(record, lake_id)
            _computed = _CONFIG_OK
            if _computed:
                _route_taken = "CONFIG_DISPATCH_BY_LAKE_ID"

    # --- VOL 12: named-handler fallthrough (priority 2 for ALL paths) ---
    # Rule 1.5 states config dispatch is "the new fallback layer BEFORE the
    # final (0.0, 0.0) return", but it was only wired into the else branch.
    # A named handler that fails therefore dropped straight to legacy and never
    # consulted the config. That gap sent biology / cosmology / planetary /
    # stellar (3.99M records across s1+s4) to the precomputed fallback.
    if _computed is None and scalar_kls == 0.0 and scalar_klc == 0.0:
        scalar_kls, scalar_klc = scalarize_from_config(record, domain_group)
        _computed = _CONFIG_OK
        if _computed:
            _route_taken = "CONFIG_AFTER_NAMED"
        else:
            scalar_kls, scalar_klc = scalarize_from_config(record, lake_id)
            _computed = _CONFIG_OK
            if _computed:
                _route_taken = "CONFIG_BY_LAKE_ID_AFTER_NAMED"

    # --- Legacy fallback (priority 3) — VOL 12: counted and named ---
    # Triggered by DISPATCH FAILURE, not by the value being 0.0. A config domain
    # that legitimately computes 0.0 keeps its zero.
    # NOTE: named handlers still cannot distinguish a computed 0.0 from a
    # failure (Vol 11.1 behaviour, deliberately preserved by this patch).
    if _computed is None:
        _computed = (scalar_kls != 0.0 or scalar_klc != 0.0)
    if not _computed:
        existing = record.get("scalar_kls")
        if existing is not None and existing != 0.0:
            scalar_kls = existing
            scalar_klc = record.get("scalar_klc", existing)
            _note(domain_group, "LEGACY_PRECOMPUTED")
        else:
            _note(domain_group, "ZERO")
    else:
        _note(domain_group, _route_taken)

    raw  = record.get("_raw_payload", {}) or {}
    meta = dict(record.get("meta", {}))
    meta.setdefault("source",           "vol10_promotion_sovereign_lake")
    meta.setdefault("ingest_timestamp", "2026-05-10T00:00:00Z")
    meta.setdefault("sovereign",        False)

    return {
        "entity_id":        record.get("entity_id") or record.get("id"),
        "domain":           domain,
        "volume":           record.get("volume") or record.get("vol"),
        "lake_id":          lake_id,
        "geometry_payload": compute_geometry_payload(raw),
        "scalar_kls":       scalar_kls,
        "scalar_klc":       scalar_klc,
        "meta":             meta,
        "_raw_payload":     raw,
    }

if __name__ == "__main__":
    start_time = time.time()
    
    print("\n" + "=" * 60)
    print("  [MONITORING TIP] Open a new terminal and run:")
    print("  python engine/sidecar.py")
    print("  to view the live byte-streaming progress dashboard.")
    print("=" * 60 + "\n")
    
    # Pre-flight: calculate total bytes for smooth global progress bar
    total_bytes = 0
    valid_lakes = []
    
    missing_lakes = []
    for lake in LAKES:
        in_path = LAKE_PATHS[lake]
        if in_path.exists():
            total_bytes += in_path.stat().st_size
            valid_lakes.append(lake)
        else:
            missing_lakes.append((lake, in_path))

    if missing_lakes:
        print("\n" + "!" * 78)
        print("  ENABLED LAKES MISSING FROM DISK -- these would be silently dropped:")
        for lake, p in missing_lakes:
            print(f"    {lake:<26} -> {p}")
        print("!" * 78 + "\n")
        if STRICT_MODE:
            print("ABORTING: enabled lake missing under KLGHS_STRICT=1.")
            print("Correct the 'path' in configs/volumes.json, or disable the lake.")
            raise SystemExit(2)
            
    global_bytes_processed = 0
    lakes_completed = 0
    
    write_heartbeat(0, 0, len(valid_lakes), 0, "Initializing Scalarization...")

    for lake in valid_lakes:
        in_path  = LAKE_PATHS[lake]
        out_path = OUTPUT_DIR / f"{lake}_scalarized.jsonl"

        print(f"Scalarizing {lake}: {in_path.name} -> {out_path.name} (mode={MODE})")

        records_this_lake = 0
        last_save = time.time()
        
        with in_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
            for line in fin:
                global_bytes_processed += len(line.encode('utf-8'))
                
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    processed_rec = scalarize_record(rec, lake)
                    fout.write(json.dumps(processed_rec, ensure_ascii=False) + "\n")
                    records_this_lake += 1
                
                if time.time() - last_save > 2.0:
                    pct = (global_bytes_processed / total_bytes) * 100 if total_bytes > 0 else 0
                    write_heartbeat(pct, time.time() - start_time, len(valid_lakes), lakes_completed, f"Crunching {lake} ({records_this_lake:,} recs)")
                    last_save = time.time()
                    
        lakes_completed += 1
        pct = (global_bytes_processed / total_bytes) * 100 if total_bytes > 0 else 0
        write_heartbeat(pct, time.time() - start_time, len(valid_lakes), lakes_completed, f"Finished {lake}")

    # --- VOL 12: dispatch attribution and strict gate ---
    offenders = dispatch_report()
    if offenders and STRICT_MODE:
        print("ABORTING: legacy fallback fired under KLGHS_STRICT=1.")
        print("Fix the field mapping in configs/scalarize.json, or set")
        print("KLGHS_STRICT=0 to run anyway (results are NOT citable).")
        raise SystemExit(2)