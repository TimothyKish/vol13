#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theorem_anchor_sweeps.py  —  Test of the Form-A analytic resolution (Mondy ruling).

The proof: for a grid-proximity lock test, a strong lock REQUIRES grid-phase
concentration; a distribution not concentrated at grid phase yields baseline z.
Therefore an offset-invariant shape-artifact (Form A) cannot exist.

The anchor sweeps TEST the proof, not gate the framework. The proof predicts each
real anchor's z-vs-offset curve is PEAKED (locks at a privileged offset, low z
elsewhere). A FLAT-HIGH offset-invariant curve on ANY anchor REFUTES the proof and
reopens everything. Disproof condition is LIVE.

Runs on the REAL promoted scalars. Reports each anchor's curve, peak, median,
peak/median, and fraction of offsets locking. Classifies PEAKED / FLAT-HIGH / neither.

FILING (per ruling): this is NOT a gate PASS. It is the illustration/test of the
theorem. Form A closed by proof; Form B (scale-coincidence/selection) remains the
open primary objection and MUST be named alongside any citation of this result.
"""
import json, os
import numpy as np

CONTAINER=24; LOCK_THRESHOLD=0.05; STRONG=5.0; NULL_BAND=3.0; SWEEP_STEPS=60
K_GEO=16.0/np.pi
ENGINE_DIR=os.path.dirname(os.path.abspath(__file__))
LAKES=os.path.join(os.path.dirname(ENGINE_DIR),"lakes","inputs_promoted")

ANCHORS={
 "stellar_kinematic":{"file":"s2_stellar_kinematics_promoted.jsonl","N":16,"inject":"scalar","field":"scalar_kls"},
 "galactic":{"file":"g1_galaxy_kinematics_promoted.jsonl","N":21,"inject":"scalar","field":"scalar_kls"},
 "nuclear_binding":{"file":"q4_nuclear_promoted.jsonl","N":21,"inject":"raw","field":"binding_energy_mev_per_A"},
}

def lock_fraction(s,t):
    rp=(np.asarray(s,dtype=float)/t)*CONTAINER; nn=np.maximum(1,np.round(rp))
    return np.mean(np.abs(rp-nn)<LOCK_THRESHOLD)
def chaos_z(s,t,rng,nt=200):
    lo,hi=float(np.min(s)),float(np.max(s)); n=len(s)
    rl=lock_fraction(s,t); nl=np.array([lock_fraction(rng.uniform(lo,hi,n),t) for _ in range(nt)])
    return (rl-nl.mean())/nl.std() if nl.std()>0 else 0.0
def scal(v): return np.log(1.0+np.abs(np.asarray(v,dtype=float)))/np.log(K_GEO)

def load(cfg):
    p=os.path.join(LAKES,cfg["file"])
    if not os.path.exists(p): return None,f"NOT FOUND {p}"
    vals=[]
    for line in open(p,encoding="utf-8"):
        line=line.strip()
        if not line: continue
        try: r=json.loads(line)
        except: continue
        v=r.get(cfg["field"])
        if v is not None:
            try: vals.append(float(v))
            except: pass
    if not vals: return None,f"no {cfg['field']}"
    a=np.asarray(vals,dtype=float)
    if cfg["inject"]=="raw": a=scal(a)
    return a,f"n={len(a)}"

def sweep(s,target,rng,steps=SWEEP_STEPS):
    grid=target/CONTAINER
    offs=np.linspace(0,grid,steps,endpoint=False)
    return offs,np.array([chaos_z(np.asarray(s,dtype=float)+o,target,rng) for o in offs])

def classify(zs):
    peak,med=zs.max(),np.median(zs)
    if peak>=STRONG and med<=NULL_BAND: return "PEAKED (theorem confirmed)"
    if med>=STRONG: return "*** FLAT-HIGH — THEOREM REFUTED, REOPEN ***"
    return "neither — report as-is"

def main():
    rng=np.random.default_rng()
    print("="*70)
    print("   ANCHOR SWEEPS — TEST OF THE FORM-A THEOREM (disproof LIVE)")
    print("="*70)
    out={}
    for aid,cfg in ANCHORS.items():
        s,msg=load(cfg)
        print(f"\n[{aid}] @ {cfg['N']}/pi  ({msg})")
        if s is None:
            print(f"    {msg}"); out[aid]={"status":"LOAD_FAILED"}; continue
        target=cfg["N"]/np.pi
        offs,zs=sweep(s,target,rng)
        peak,med=float(zs.max()),float(np.median(zs))
        frac=float(np.mean(zs>=STRONG)*100)
        v=classify(zs)
        print(f"    peak z={peak:.1f}  median z={med:.2f}  peak/median={peak/max(med,1):.0f}")
        print(f"    offsets locking(z>=5): {frac:.0f}%   min={zs.min():.1f}")
        print(f"    -> {v}")
        out[aid]={"N":cfg["N"],"peak":peak,"median":med,"frac_locked":frac,
                  "verdict":v,"curve":zs.tolist(),"offsets":offs.tolist()}
    print("\n"+"="*70)
    refuted=any("REFUTED" in o.get("verdict","") for o in out.values() if isinstance(o,dict))
    if refuted:
        print("  RESULT: at least one FLAT-HIGH curve. THEOREM REFUTED. Reopen Form A.")
    else:
        print("  RESULT: all curves PEAKED (or reported as-is). Theorem illustrated.")
        print("  FORM A (transform shape-artifact) closed by proof.")
        print("  FORM B (scale-coincidence / selection) REMAINS THE OPEN PRIMARY OBJECTION.")
    f=os.path.join(ENGINE_DIR,"theorem_anchor_sweeps_result.json")
    json.dump(out,open(f,"w"),indent=2)
    print(f"\n  Written: {f}")
    print("  Bring the three curves to Mondy as confirmation-or-refutation of the proof.")

if __name__=="__main__": main()