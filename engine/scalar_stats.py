#!/usr/bin/env python3
import json, os
import numpy as np

LAKES = {
    "s2_stellar_kinematics": ("../lakes/inputs_promoted/s2_stellar_kinematics_promoted.jsonl", "scalar_kls"),
    "b5_pdb_protein":        ("../lakes/inputs_promoted/b5_pdb_protein_promoted.jsonl", "angle_degrees"),
    "p1_orbital_periods":    ("../lakes/inputs_promoted/p1_orbital_periods_promoted.jsonl", "scalar_kls"),
}
K = 16.0/np.pi

for name,(path,field) in LAKES.items():
    if not os.path.exists(path):
        print(f"{name}: FILE NOT FOUND {path}"); continue
    vals=[]
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            rec=json.loads(line)
            v=rec.get(field)
            if v is not None:
                try: vals.append(float(v))
                except: pass
    a=np.asarray(vals,dtype=float)
    print(f"\n[{name}]  field='{field}'  n={len(a)}")
    print(f"  RAW field   : min={a.min():.4g} max={a.max():.4g} mean={a.mean():.4g} median={np.median(a):.4g}")
    # what the scalar looks like: for s2/p1 the field IS the scalar; for b5 it's raw degrees
    s = a if field=="scalar_kls" else np.log(1.0+np.abs(a))/np.log(K)
    r = s/(16/np.pi)
    print(f"  SCALAR      : min={s.min():.4f} max={s.max():.4f} mean={s.mean():.4f}")
    print(f"  ratio s/(16/pi): min={r.min():.4f} max={r.max():.4f}  -> node_index range floor: {int(np.floor(r.min()))}..{int(np.floor(r.max()))}")
    # also the 22/pi register for orbital
    r22 = s/(22/np.pi)
    print(f"  ratio s/(22/pi): min={r22.min():.4f} max={r22.max():.4f}  -> node_index range: {int(np.floor(r22.min()))}..{int(np.floor(r22.max()))}")