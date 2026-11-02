"""Campagne d'experiences. Reprise possible : les jobs deja dans results/*.jsonl sont sautes.

usage : python run_all.py [--workers 6] [--budget 120] [--seeds 3] [--sens-budget 60]
"""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS = HERE.parent / "inputs"
RES = HERE / "results"
SENS_INSTANCES = ["instance01", "instance02", "instance04"]
SENS_PERTURB = [0.01, 0.05, 0.10, 0.20]
SENS_ITEMS = [300, 5000]


def key(j):
    return tuple(j)


def run(job, timeout):
    algo, inst, budget, seed, perturb, items, tag = job
    f = RES / f"{tag}.jsonl"
    cmd = [sys.executable, "-I", str(HERE / "run_one.py"), algo, str(INPUTS / f"{inst}.txt"),
           str(budget), str(seed), str(perturb), str(items)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env={**__import__("os").environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        line = p.stdout.strip().splitlines()[-1]
        rec = json.loads(line)
        rec["tag"] = tag
        with open(f, "a", encoding="utf8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"OK  {tag} {algo} {inst} s{seed} p{perturb} i{items} -> {rec['score']:,}", flush=True)
    except Exception as e:
        print(f"ERR {tag} {algo} {inst} s{seed}: {e!r} {getattr(p,'stderr','')[-300:] if 'p' in dir() else ''}", flush=True)


def done_set():
    s = set()
    for f in RES.glob("*.jsonl"):
        for l in f.read_text(encoding="utf8").splitlines():
            r = json.loads(l)
            s.add((r["tag"], r["algo"], r["instance"], r["budget"], r["seed"], r["perturb"], r["max_items"]))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget", type=float, default=120)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--sens-budget", type=float, default=60)
    a, _ = ap.parse_known_args()
    RES.mkdir(exist_ok=True)
    insts = sorted(p.stem for p in INPUTS.glob("instance*.txt"))
    jobs = []
    for i in insts:
        jobs.append(("greedy", i, a.budget, 0, 0.05, 1500, "main"))
        jobs.append(("gratio", i, a.budget, 0, 0.05, 1500, "main"))
        jobs.append(("ls", i, a.budget, 0, 0.05, 1500, "main"))
        for s in range(a.seeds):
            jobs.append(("dp", i, a.budget, s, 0.05, 1500, "main"))
    for i in SENS_INSTANCES:
        for s in range(2):
            for p in SENS_PERTURB:
                jobs.append(("dp", i, a.sens_budget, s, p, 1500, "sens"))
            for it in SENS_ITEMS:
                jobs.append(("dp", i, a.sens_budget, s, 0.05, it, "sens"))
    done = done_set()
    todo = [j for j in jobs if (j[6], j[0], j[1], j[2], j[3], j[4], j[5]) not in done]
    # gros jobs d'abord pour lisser la charge
    todo = [j for j in todo if j[6] == "sens" or "--all" in sys.argv]
    todo.sort(key=lambda j: -(INPUTS / f"{j[1]}.txt").stat().st_size)
    print(f"{len(todo)} jobs a lancer sur {len(jobs)}", flush=True)
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(lambda j: run(j, j[2] * 3 + 600), todo))


if __name__ == "__main__":
    main()
