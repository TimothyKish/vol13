# Sovereign Lake Build Guide: s19 Auger Electrons

**Domain:** `electron_auger_kinematic`
**Source:** NIST X-Ray / Auger Transition Energies Database
**Physical Quantity:** Absolute Kinetic Energy of ejected Auger electrons (eV)
**Fleet Tier:** Tier 1 (Raw Kinematic, Independent Trigger)

## The Chain of Custody

Because NIST provides this dataset via a CGI search form, manual extraction poses a reproducibility risk. To ensure a strictly deterministic pull, we bypass the web UI and use a direct `GET` request containing every element parameter explicitly.

### Step 1: Raw Ingestion
Download the raw ASCII dataset directly from the NIST server using the following pre-configured URL. This explicitly requests a tab-delimited format (`download=tab`) for all elements (Neon through Fermium), converted to electron-volts (`units=eV`).

**Direct NIST Endpoint:**
```text
[https://physics.nist.gov/cgi-bin/XrayTrans/search.pl?download=tab&element=Ne&element=Na&element=Mg&element=Al&element=Si&element=P&element=S&element=Cl&element=Ar&element=K&element=Ca&element=Sc&element=Ti&element=V&element=Cr&element=Mn&element=Fe&element=Co&element=Ni&element=Cu&element=Zn&element=Ga&element=Ge&element=As&element=Se&element=Br&element=Kr&element=Rb&element=Sr&element=Y&element=Zr&element=Nb&element=Mo&element=Tc&element=Ru&element=Rh&element=Pd&element=Ag&element=Cd&element=In&element=Sn&element=Sb&element=Te&element=I&element=Xe&element=Cs&element=Ba&element=La&element=Ce&element=Pr&element=Nd&element=Pm&element=Sm&element=Eu&element=Gd&element=Tb&element=Dy&element=Ho&element=Er&element=Tm&element=Yb&element=Lu&element=Hf&element=Ta&element=W&element=Re&element=Os&element=Ir&element=Pt&element=Au&element=Hg&element=Tl&element=Pb&element=Bi&element=Po&element=At&element=Rn&element=Fr&element=Ra&element=Ac&element=Th&element=Pa&element=U&element=Np&element=Pu&element=Am&element=Cm&element=Bk&element=Cf&element=Es&element=Fm&trans=All&lower=&upper=&units=eV](https://physics.nist.gov/cgi-bin/XrayTrans/search.pl?download=tab&element=Ne&element=Na&element=Mg&element=Al&element=Si&element=P&element=S&element=Cl&element=Ar&element=K&element=Ca&element=Sc&element=Ti&element=V&element=Cr&element=Mn&element=Fe&element=Co&element=Ni&element=Cu&element=Zn&element=Ga&element=Ge&element=As&element=Se&element=Br&element=Kr&element=Rb&element=Sr&element=Y&element=Zr&element=Nb&element=Mo&element=Tc&element=Ru&element=Rh&element=Pd&element=Ag&element=Cd&element=In&element=Sn&element=Sb&element=Te&element=I&element=Xe&element=Cs&element=Ba&element=La&element=Ce&element=Pr&element=Nd&element=Pm&element=Sm&element=Eu&element=Gd&element=Tb&element=Dy&element=Ho&element=Er&element=Tm&element=Yb&element=Lu&element=Hf&element=Ta&element=W&element=Re&element=Os&element=Ir&element=Pt&element=Au&element=Hg&element=Tl&element=Pb&element=Bi&element=Po&element=At&element=Rn&element=Fr&element=Ra&element=Ac&element=Th&element=Pa&element=U&element=Np&element=Pu&element=Am&element=Cm&element=Bk&element=Cf&element=Es&element=Fm&trans=All&lower=&upper=&units=eV)