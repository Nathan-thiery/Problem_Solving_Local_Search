
import sys
import time
import random
from pathlib import Path

import numpy as np

from Local_Search import (
    Main, PrecomputeStructures, AddVideo, RemoveVideo, ReoptimizeCache,
    ComputeLocalCandidates, FinalScore, WriteOutput, SEP, SUB,
)
from Global_Greedy import GlobalGreedy


def Knapsack01(values, sizes, capacity):
   
    n = len(values)
    if n == 0:
        return 0.0, []
    if int(sizes.sum()) <= capacity:            # tout rentre : rien a optimiser
        return float(values.sum()), list(range(n))

    dp = np.zeros(capacity + 1, dtype=np.float64)           # dp[cap] = meilleur gain avec cap Mo !!!!
    keep = np.zeros((n, capacity + 1), dtype=bool)          # keep[i, cap] = video i prise ?
    cand = np.empty(capacity + 1, dtype=np.float64)         # tampon reutilise
    for i in range(n):
        w = int(sizes[i])
        if w > capacity:
            continue
        m = capacity + 1 - w
        np.add(dp[:m], values[i], out=cand[:m])             
        np.greater(cand[:m], dp[w:], out=keep[i, w:])       # cest mieux avec ou sans i ?
        np.maximum(dp[w:], cand[:m], out=dp[w:])            # garder le meilleur comm tjrs :)

    # Reconstruction de la solution
    chosen, c = [], int(np.argmax(dp))
    for i in range(n - 1, -1, -1):
        if keep[i, c]:
            chosen.append(i)
            c -= int(sizes[i])
    return float(dp.max()), chosen


def PruneCandidates(cand_videos, values, sizes, capacity, forced, max_items):
 
    n = len(cand_videos)
    if n <= max_items:
        return np.arange(n)
    order = np.argsort(-(values / sizes))
    cum = np.cumsum(sizes[order])
    k = int(np.searchsorted(cum, capacity)) + 1          
    keep_n = min(n, max(max_items, 3 * k))
    idx = set(order[:keep_n].tolist())
    if forced:
        pos = np.flatnonzero(np.isin(cand_videos, list(forced)))
        idx.update(pos.tolist())
    return np.array(sorted(idx), dtype=np.int64)


def ReoptimizeCacheDP(cache_id, data, structures, S_np, V, output, max_items=1500):
    """Vide le cache puis le remplit de avec DP 
    """
    X = data["X"]
    old = list(output[cache_id])
    delta = 0.0
    for v in old:
        delta += RemoveVideo(v, cache_id, structures)

    cand, vals = ComputeLocalCandidates(cache_id, structures, V)
    new = []
    if cand.size:
        sizes = S_np[cand]
        sel = PruneCandidates(cand, vals, sizes, X, old, max_items)
        best_val, chosen = Knapsack01(vals[sel], sizes[sel].astype(np.int64), X)
        old_val = float(vals[np.isin(cand, old)].sum()) if old else 0.0
        if best_val > old_val + 1e-9:
            new = [int(cand[sel[i]]) for i in chosen]

    if not new:                       # le cas ou pas mieux 
        for v in old:
            delta += AddVideo(v, cache_id, structures)
        output[cache_id] = set(old)
        return max(delta, 0.0)

    for v in new:
        delta += AddVideo(v, cache_id, structures)
    output[cache_id] = set(new)
    return delta


def RandomFill(cache_id, data, structures, S_np, V, output, rng):
    """ajout de random pour remplir le temps qui reste on perds pas de temps hh"""
    cand, vals = ComputeLocalCandidates(cache_id, structures, V)
    if cand.size == 0:
        return 0.0
    u = np.array([rng.random() for _ in range(len(vals))]) + 1e-300
    keys = np.log(u) / vals                                 
    order = np.argsort(-keys)
    cap, delta = data["X"], 0.0
    for i in order:
        v = int(cand[i])
        if S_np[v] <= cap:
            cap -= int(S_np[v])
            delta += AddVideo(v, cache_id, structures)
            output[cache_id].add(v)
    return delta


STOP_REL_1A = 1e-5      


def CacheOrder(data):
    
    C = data["C"]
    weight = np.zeros(C)
    for e, reqs in data["requests"].items():
        ep = data["endpoints"][e]
        tot = sum(reqs.values())
        for c, lat in ep["cache_connections"]:
            weight[c] += tot * (ep["data_center_latency"] - lat)
    return list(np.argsort(-weight))


def ReoptimizeCacheRatio(cache_id, data, structures, S_np, V, output):

    return ReoptimizeCache(cache_id, data, structures, S_np, V, output)


def Descent(order, data, structures, S_np, V, output, deadline, rng, verbose, tag="", reopt=None,
            stop_rel=0.0, base=0.0):
    
    reopt = reopt or ReoptimizeCacheDP
    total, rnd = 0.0, 0
    while True:
        rnd += 1
        gain = 0.0
        for c in order:
            gain += reopt(c, data, structures, S_np, V, output)
            if time.time() > deadline:
                return total + gain, True
        total += gain
        if verbose:
            print(f"   {tag}round {rnd:>2} | gain = {gain:>16,.0f} ms")
        if gain <= 1e-9:
            return total, False
        if stop_rel > 0 and gain < stop_rel * (base + total):
            if verbose:
                print(f"   {tag}gain < {stop_rel:g} du total : on passe à la suite")
            return total, False
        order = list(order)
        rng.shuffle(order)


def CacheNeighbors(data):
    
    E, C = data["E"], data["C"]
    A = np.zeros((E, C), dtype=np.int32)
    for ep in data["endpoints"]:
        for c, _ in ep["cache_connections"]:
            A[ep["id"], c] = 1
    M = (A.T @ A) > 0
    np.fill_diagonal(M, False)
    return [np.flatnonzero(M[c]).tolist() for c in range(C)]


def LocalDescent(queue, nb, data, structures, S_np, V, output, deadline, reopt):
    
    from collections import deque
    q, inq, total = deque(queue), set(queue), 0.0
    while q:
        c = q.popleft()
        inq.discard(c)
        g = reopt(c, data, structures, S_np, V, output)
        if g > 1e-9:
            total += g
            for n in nb[c]:
                if n not in inq:
                    q.append(n)
                    inq.add(n)
        if time.time() > deadline:
            return total, True
    return total, False


def Restore(best, output, structures, data):
    
    diff = [c for c in range(data["C"]) if output[c] != best[c]]
    for c in diff:
        for v in list(output[c]):
            RemoveVideo(v, c, structures)
    for c in diff:
        for v in best[c]:
            AddVideo(v, c, structures)
        output[c] = set(best[c])


def SolveDP(data, time_budget=120, seed=0, perturb_frac=0.05, verbose=True):
    t0 = time.time()
    deadline = t0 + time_budget
    rng = random.Random(seed)
    V, C = data["V"], data["C"]
    S_np = np.array(data["S"], dtype=np.float64)

    structures = PrecomputeStructures(data)
    output = {c: set() for c in range(C)}
    total_req = sum(n for r in data["requests"].values() for n in r.values())
    to_score = lambda ms: int(ms * 1000 // total_req)

    # glouton GLOBAL sur les paires (video, cache)
    cur = 0.0
    for c, vids in GlobalGreedy(data, verbose=verbose).items():
        for v in vids:
            cur += AddVideo(v, c, structures)
        output[c] = set(vids)
    if verbose:
        print(f"[GG] Score glouton global = {to_score(cur):,} | t = {time.time()-t0:.1f}s")
        print(SUB)

    # descente rapide puis descente exacte (DP) si le temps le permet
    order = CacheOrder(data)
    if verbose:
        print("[LS] Phase 1a : descente rapide (ratio + échanges)")
    # la descente rapide s'arrete quand un tour rapporte < 1/100 000 du total
    
    g, timeout = Descent(order, data, structures, S_np, V, output, deadline, rng, verbose,
                         reopt=ReoptimizeCacheRatio, stop_rel=STOP_REL_1A, base=cur)
    cur += g
    if not timeout:
        if verbose:
            print("[LS] Phase 1b : descente exacte (sac à dos DP par cache)")
        g, timeout = Descent(order, data, structures, S_np, V, output, deadline, rng, verbose)
        cur += g
    best, best_ms = {c: set(v) for c, v in output.items()}, cur
    if verbose:
        print(f"[DP] Optimum local : score = {to_score(cur):,} | t = {time.time()-t0:.1f}s")
        print(SUB)

    # Random ce qu'il reste du tenps
    it = accepted = 0
    k = max(1, int(perturb_frac * C))
    nb = CacheNeighbors(data)

    ils_reopt = ReoptimizeCacheDP if C * data["X"] <= 1_500_000 else ReoptimizeCacheRatio
    while not timeout and time.time() < deadline:
        it += 1
        victims = rng.sample(range(C), k)
        for c in victims:                       
            for v in list(output[c]):
                cur += RemoveVideo(v, c, structures)
            output[c] = set()
            cur += RandomFill(c, data, structures, S_np, V, output, rng)  
        vs = set(victims)
        order = sorted({n for c in victims for n in nb[c]} - vs)
        rng.shuffle(order)
        order += victims
        g, timeout = LocalDescent(order, nb, data, structures, S_np, V, output, deadline, ils_reopt)
        cur += g
        if cur > best_ms + 1e-6:
            best, best_ms = {c: set(v) for c, v in output.items()}, cur
            accepted += 1
            if verbose:
                print(f"[ILS] it {it:>3} | nouveau meilleur score = {to_score(best_ms):,} | t = {time.time()-t0:.1f}s")
        else:
            Restore(best, output, structures, data)
            cur = best_ms

    if verbose:
        print(f"[ILS] {it} perturbations, {accepted} acceptées | t = {time.time()-t0:.1f}s")
    return best


if __name__ == "__main__":
    t_global = time.time()
    filename = sys.argv[1] if len(sys.argv) > 1 else "../inputs/me_at_the_zoo.in"
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 120
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    data = Main(filename)
    best = SolveDP(data, time_budget=budget, seed=seed)
    WriteOutput(best, Path("outputs") / f"{data['name']}_dp.out")
    chrono, score = FinalScore(data, best)
    print(SEP)
    print(f"   Score (gain moyen, µs)  : {score:,}")
    print(f"   Temps total             : {time.time() - t_global:.1f}s")
    print(SEP)