"""TSE live-count reader and state-weighted projection (Brazil 2026 general).

Usage:
  python3 strategy/tools/tse.py keys                 # dump top-level keys of the BR file
  python3 strategy/tools/tse.py president            # national raw + per-state projection
  python3 strategy/tools/tse.py office <uf> <cargo>  # e.g. office rj 3 (gov), office sp 5 (senate)

The national running total over-weights early-counting states (South/Southeast/
Centre-West count first; the Northeast lags), so the raw percentage at 10-50%
counted is biased. The projection extrapolates each state's current shares to
its full expected valid vote (state valid so far / state pst), which removes
most of that bias. Remaining error: within-state counting order (capitals vs
interior), which this does not model.

Source: resultados.tse.jus.br static JSON (election 6257 = federal 1st round,
6259 = state 1st round). Numbers come as pt-BR strings ("1.234", "12,34").
"""

import json
import sys
import urllib.request

BASE = "https://resultados.tse.jus.br/oficial/ele2026"
UFS = ("ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc "
       "se sp to zz").split()


def get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def num(s):
    if s is None or s == "":
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    return float(str(s).replace(".", "").replace(",", "."))


def candidates(d):
    """Flatten candidate rows across the possible container shapes."""
    out = []
    for c in d.get("cand", []):
        out.append(c)
    for carg in d.get("carg", []):
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                out.extend(par.get("cand", []))
    return out


def summary(d):
    cands = {c.get("nm"): num(c.get("vap")) for c in candidates(d)}
    vv = num(d.get("vv")) or sum(cands.values())
    return {"dg": d.get("dg"), "hg": d.get("hg"), "pst": num(d.get("pst")), "vv": vv,
            "cands": cands}


def path(eleicao, uf, cargo):
    return f"{eleicao}/dados/{uf}/{uf}-c{cargo:04d}-e{eleicao:06d}-u.json"


def president():
    nat = summary(get(path(6257, "br", 1)))
    print(f"BR raw: generated {nat['dg']} {nat['hg']}, pst {nat['pst']:.2f}%")
    for nm, v in sorted(nat["cands"].items(), key=lambda kv: -kv[1])[:6]:
        print(f"  {nm:45s} {100 * v / nat['vv']:6.2f}%")
    proj = {}
    proj_vv = 0.0
    rows = []
    for uf in UFS:
        try:
            s = summary(get(path(6257, uf, 1)))
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"  {uf}: fetch failed ({e})")
            continue
        if s["pst"] <= 0 or s["vv"] <= 0:
            rows.append((uf, s["pst"], None))
            # unknown shape: fall back to the national raw shares, flagged below
            continue
        scale = 100.0 / s["pst"]
        full_vv = s["vv"] * scale
        proj_vv += full_vv
        for nm, v in s["cands"].items():
            proj[nm] = proj.get(nm, 0.0) + (v / s["vv"]) * full_vv
        rows.append((uf, s["pst"], full_vv))
    zero = [r[0] for r in rows if r[2] is None]
    print(f"Projection (state shares x expected state valid vote); states with 0% counted: {zero}")
    for nm, v in sorted(proj.items(), key=lambda kv: -kv[1])[:6]:
        print(f"  {nm:45s} {100 * v / proj_vv:6.2f}%")
    print("per-state pst: " + " ".join(f"{u}:{p:.0f}" for u, p, _ in rows))


def office(uf, cargo):
    s = summary(get(path(6259, uf, int(cargo))))
    print(f"{uf.upper()} cargo {cargo}: generated {s['dg']} {s['hg']}, pst {s['pst']:.2f}%")
    for nm, v in sorted(s["cands"].items(), key=lambda kv: -kv[1])[:6]:
        print(f"  {nm:45s} {100 * v / s['vv']:6.2f}%")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "president"
    if cmd == "keys":
        d = get(path(6257, "br", 1))
        print({k: (v if not isinstance(v, list) else f"list[{len(v)}]") for k, v in d.items()})
        cs = candidates(d)
        print(cs[0] if cs else "no cand rows found")
    elif cmd == "president":
        president()
    elif cmd == "office":
        office(sys.argv[2], sys.argv[3])
