"""

Matrices denses numpy :  G[v, c] = gain marginal actuel (ms) de placer v dans c
                         R[v, c] = G[v, c] / taille(v), ou -inf si impossible
"""
import time
import numpy as np


def GlobalGreedy(data, verbose=True, alpha=1.0):
    t0 = time.time()
    V, E, C, X = data["V"], data["E"], data["C"], data["X"]
    S = np.array(data["S"], dtype=np.float64)

    # latence endpoint
    conn_c = [np.array([c for c, _ in ep["cache_connections"]], dtype=np.int64) for ep in data["endpoints"]]
    conn_l = [np.array([l for _, l in ep["cache_connections"]], dtype=np.float64) for ep in data["endpoints"]]
    lat = [dict(ep["cache_connections"]) for ep in data["endpoints"]]
    LD = np.array([ep["data_center_latency"] for ep in data["endpoints"]], dtype=np.float64)

    # Requetes  par video ---> [(e, n), ...]
    req_by_video = [[] for _ in range(V)]
    best = {}                                     # meilleur latence pour ce moment
    G = np.zeros((V, C), dtype=np.float64)
    for e, reqs in data["requests"].items():
        if not reqs or conn_c[e].size == 0:
            continue
        vids = np.fromiter(reqs.keys(), dtype=np.int64, count=len(reqs))
        cnts = np.fromiter(reqs.values(), dtype=np.float64, count=len(reqs))
        G[np.ix_(vids, conn_c[e])] += np.outer(cnts, LD[e] - conn_l[e])
        for v, n in reqs.items():
            req_by_video[v].append((e, n))
            best[(e, v)] = LD[e]

    cap = np.full(C, X, dtype=np.float64)
    R = G / np.power(S, alpha)[:, None]
    R[G <= 0] = -np.inf
    R[S[:, None] > cap[None, :]] = -np.inf

    output = {c: set() for c in range(C)}
    P = np.zeros((V, C), dtype=bool)
    placed = 0



    rowmax = R.max(axis=1)
    if verbose:
        print(f"[GG] Matrice {V}x{C} construite en {time.time()-t0:.1f}s")
# Chercher la meilleure paire  sur V valeurs
    while True:
        v = int(np.argmax(rowmax))
        c = int(np.argmax(R[v]))
        if not np.isfinite(R[v, c]) or R[v, c] <= 0:
            break

        # Placement de v dans c
        output[c].add(v)
        P[v, c] = True
        cap[c] -= S[v]
        placed += 1

        # Mise a jour des gains marginaux de la vidio v sur tous les caches
        for e, n in req_by_video[v]:
            Lc = lat[e].get(c)
            b_old = best[(e, v)]
            if Lc is None or Lc >= b_old:
                continue
            le = conn_l[e]
            G[v, conn_c[e]] -= n * (np.maximum(0.0, b_old - le) - np.maximum(0.0, Lc - le))
            best[(e, v)] = Lc

        row = G[v] / (S[v] ** alpha)
        row[G[v] <= 1e-9] = -np.inf
        row[cap < S[v]] = -np.inf
        row[P[v]] = -np.inf                      
        R[v] = row
        rowmax[v] = row.max()

        # le cas ou la cache c a moins de place.
        newly = np.flatnonzero((S > cap[c]) & np.isfinite(R[:, c]))
        if newly.size:
            R[newly, c] = -np.inf
            rowmax[newly] = R[newly].max(axis=1)     
    if verbose:
        print(f"[GG] {placed:,} placements en {time.time()-t0:.1f}s")
    return output