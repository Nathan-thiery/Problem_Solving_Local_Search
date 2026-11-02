"""Worker : une execution (algo, instance, seed) -> une ligne JSON sur stdout.

usage : python run_one.py <algo: greedy|ls|dp> <instance> <budget_s> <seed> [perturb_frac] [max_items]

La courbe de convergence est obtenue SANS modifier les algos : on enveloppe
AddVideo / RemoveVideo (qui retournent le delta de gain) et on echantillonne le
meilleur gain cumule rencontre (un etat reellement atteint, jamais surestime).
"""
import io
import json
import os
import sys
import time
import contextlib
from pathlib import Path

ALGOS = Path(__file__).resolve().parent.parent / "Algos_V2"
sys.path.insert(0, str(ALGOS))

import Local_Search as LS            # noqa: E402
import Local_Search_DP as DP         # noqa: E402
import Global_Greedy as GG           # noqa: E402
import Greedy_Ratio as GR            # noqa: E402


def instrument(curve, t_start):
    state = {"cum": 0.0, "best": 0.0, "last": -1.0}

    def sample():
        t = time.time() - t_start[0]
        if state["best"] < state["cum"]:
            state["best"] = state["cum"]
        if t - state["last"] >= 0.25:
            curve.append((round(t, 2), state["best"]))
            state["last"] = t

    def wrap(fn):
        def inner(*a, **k):
            d = fn(*a, **k)
            state["cum"] += d
            sample()
            return d
        return inner

    add, rem = wrap(LS.AddVideo), wrap(LS.RemoveVideo)
    for mod in (LS, DP):
        mod.AddVideo, mod.RemoveVideo = add, rem
    return state


def main():
    algo, inst, budget, seed = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
    perturb = float(sys.argv[5]) if len(sys.argv) > 5 else 0.05
    max_items = int(sys.argv[6]) if len(sys.argv) > 6 else 1500
    if max_items != 1500:
        DP.ReoptimizeCacheDP.__defaults__ = (max_items,)

    t_load = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        data = LS.Main(inst)
    load_s = time.time() - t_load
    total_req = sum(n for r in data["requests"].values() for n in r.values())

    curve, t0 = [], [time.time()]
    state = instrument(curve, t0)
    t0[0] = time.time()

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if algo == "greedy":
            out = {c: set(v) for c, v in GG.GlobalGreedy(data, verbose=False).items()}
        elif algo == "gratio":
            out = {c: set(v) for c, v in GR.Greedy(data)["output"].items()}
        elif algo == "ls":
            out = LS.LocalSearch(data, max_rounds=10, time_budget_seconds=budget, verbose=True)
        elif algo == "dp":
            out = DP.SolveDP(data, time_budget=budget, seed=seed, perturb_frac=perturb, verbose=True)
        else:
            raise SystemExit("algo inconnu")
    run_s = time.time() - t0[0]

    _, score = LS.FinalScore(data, out)
    to_score = lambda ms: int(ms * 1000 // total_req)
    if algo in ("greedy", "gratio"):       # les gloutons ne passe pas par AddVideo
        curve = [(round(run_s, 2), score)]
    else:
        curve = [(t, to_score(g)) for t, g in curve]
        curve.append((round(run_s, 2), score))
    used = sum(sum(int(data["S"][v]) for v in vs) for vs in out.values())
    print(json.dumps({
        "algo": algo, "instance": Path(inst).stem, "seed": seed, "budget": budget,
        "perturb": perturb, "max_items": max_items,
        "V": data["V"], "E": data["E"], "C": data["C"], "X": data["X"],
        "R": total_req, "n_endpoint_lines": sum(len(r) for r in data["requests"].values()),
        "score": score, "run_s": round(run_s, 2), "load_s": round(load_s, 2),
        "fill": used / (data["C"] * data["X"]), "curve": curve,
    }))


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    main()
