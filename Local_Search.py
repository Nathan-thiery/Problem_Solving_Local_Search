import time
from pathlib import Path
import numpy as np
import sys

from Greedy_Ratio import Greedy


SEP = "=" * 60
SUB = "-" * 60


def Main(filename = "./instances/instance2.in"):
    candidates = [
        Path("instances") / filename,
        Path(filename),
    ]

    for path in candidates:
        if path.exists():
            print(SEP)
            print(f" Lecture du fichier : {path}")
            with path.open("r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line:
                    raise ValueError(f"Le fichier {path} est vide.")

                values = list(map(int, first_line.split()))
                if len(values) < 5:
                    raise ValueError(f"Le fichier {path} ne contient pas assez d'entiers sur la première ligne.")

                V, E, R, C, X = values[:5]

                S = list(map(int, f.readline().strip().split()))
                if len(S) < V:
                    raise ValueError(f"Le fichier {path} ne contient pas assez de tailles de vidéos.")

                endpoints = []
                for endpoint_id in range(E):
                    line = f.readline().strip().split()
                    if len(line) < 2:
                        raise ValueError(f"Endpoint {endpoint_id}: ligne incomplète.")

                    LD, K = map(int, line)
                    cache_connections = {}
                    for _ in range(K):
                        c_line = f.readline().strip().split()
                        if len(c_line) < 2:
                            raise ValueError(f"Endpoint {endpoint_id}: ligne de cache incomplète.")
                        c, Lc = map(int, c_line)
                        cache_connections[c] = Lc
                    cache_connections = sorted(cache_connections.items(), key=lambda item: item[1])

                    endpoints.append({
                        "id": endpoint_id,
                        "data_center_latency": LD,
                        "cache_connections": cache_connections,
                    })

                Requests = {}
                for _ in range(R):
                    line = f.readline().strip().split()
                    if len(line) < 3:
                        raise ValueError("Ligne de requête incomplète.")
                    v, e, n = map(int, line)
                    endpoint_requests = Requests.setdefault(e, {})
                    endpoint_requests[v] = endpoint_requests.get(v, 0) + n

                print(f"   Vidéos    V = {V:>8,}")
                print(f"   Endpoints E = {E:>8,}")
                print(f"   Requêtes  R = {R:>8,}")
                print(f"   Caches    C = {C:>8,}   (capacité X = {X:,} MB)")
                print(SEP)

                return {
                    "name": path.stem,
                    "endpoints": endpoints,
                    "requests": Requests,
                    "V": V,
                    "E": E,
                    "R": R,
                    "C": C,
                    "X": X,
                    "S": S
                }

    raise FileNotFoundError(f"Fichier introuvable dans les chemins spécifiés : {filename}")



def PrecomputeStructures(data):
    E, V = data["E"], data["V"]

    video_ids_arr = [None] * E
    counts_arr = [None] * E
    best_latency_arr = [None] * E
    video_id_to_idx = [None] * E
    LD_arr = [0.0] * E

    for endpoint_id in range(E):
        requests = data["requests"].get(endpoint_id, {})
        LD = data["endpoints"][endpoint_id]["data_center_latency"]
        LD_arr[endpoint_id] = float(LD)

        if requests:
            v_ids = np.fromiter(requests.keys(), dtype=np.int64, count=len(requests))
            counts = np.fromiter(requests.values(), dtype=np.float64, count=len(requests))
        else:
            v_ids = np.empty(0, dtype=np.int64)
            counts = np.empty(0, dtype=np.float64)

        video_ids_arr[endpoint_id] = v_ids
        counts_arr[endpoint_id] = counts
        best_latency_arr[endpoint_id] = np.full(v_ids.shape[0], LD, dtype=np.float64)
        video_id_to_idx[endpoint_id] = {int(v): i for i, v in enumerate(v_ids)}   # index des videos dans les tableaux du dessus

    reverse_conn = {c: [] for c in range(data["C"])}
    for endpoint in data["endpoints"]:
        for cache_id, latency in endpoint["cache_connections"]:
            reverse_conn[cache_id].append((endpoint["id"], float(latency)))

    providers = [dict() for _ in range(E)]  # providers[e][idx] = [(cache_id, latency), ...]

    return {
        "video_ids_arr": video_ids_arr,
        "counts_arr": counts_arr,
        "best_latency_arr": best_latency_arr,
        "video_id_to_idx": video_id_to_idx,
        "LD_arr": LD_arr,
        "reverse_conn": reverse_conn,
        "providers": providers,
    }


def AddVideo(video_id, cache_id, structures):
    """Place video_id dans cache_id. Met à jour l'état et renvoie le gain de score (ms)."""
    delta = 0.0
    for endpoint_id, Lc in structures["reverse_conn"][cache_id]:
        idx = structures["video_id_to_idx"][endpoint_id].get(video_id)
        if idx is None:
            continue  # cet endpoint ne demande pas cette vidéo

        providers_e = structures["providers"][endpoint_id]
        providers_e.setdefault(idx, []).append((cache_id, Lc))

        old_best = structures["best_latency_arr"][endpoint_id][idx]
        if Lc < old_best:
            count = structures["counts_arr"][endpoint_id][idx]  # nb de fois où la vidéo est demandée
            delta += count * (old_best - Lc)
            structures["best_latency_arr"][endpoint_id][idx] = Lc
    return delta


def RemoveVideo(video_id, cache_id, structures):
    """Retire video_id de cache_id. Recalcule correctement la nouvelle
    meilleure latence pour les endpoints affectés, et renvoie la variation de score (ms, normalement <= 0)."""
    delta = 0.0
    for endpoint_id, Lc in structures["reverse_conn"][cache_id]:
        idx = structures["video_id_to_idx"][endpoint_id].get(video_id)
        if idx is None:
            continue

        providers_e = structures["providers"][endpoint_id]    # paires (cache, latence) associés aux vidéos d'un endpoint
        lst = providers_e.get(idx)
        if not lst:
            continue
        if (cache_id, Lc) in lst:
            lst.remove((cache_id, Lc))

        old_best = structures["best_latency_arr"][endpoint_id][idx]
        if Lc == old_best:
            # ce cache fournissait la meilleure latence actuelle : il faut
            # recalculer la nouvelle meilleure option restante.
            if lst:
                new_best = min(latency for (_c, latency) in lst)
            else:
                new_best = structures["LD_arr"][endpoint_id]
            if new_best > old_best:
                count = structures["counts_arr"][endpoint_id][idx]
                delta -= count * (new_best - old_best)
                structures["best_latency_arr"][endpoint_id][idx] = new_best

        if not lst:
            providers_e.pop(idx, None)
    return delta


def ComputeLocalCandidates(cache_id, structures, V):
    """Valeur marginale actuelle de chaque vidéo candidate pour ce cache."""
    local_value = np.zeros(V, dtype=np.float64)
    for endpoint_id, Lc in structures["reverse_conn"][cache_id]:
        v_ids = structures["video_ids_arr"][endpoint_id]
        if v_ids.size == 0:
            continue
        best = structures["best_latency_arr"][endpoint_id]
        marginal_gain = np.maximum(0.0, best - Lc) * structures["counts_arr"][endpoint_id]
        local_value[v_ids] += marginal_gain

    candidate_videos = np.nonzero(local_value)[0]
    return candidate_videos, local_value[candidate_videos]


def ImproveByExchanges(chosen, candidate_videos, values, sizes, capacity, alpha=1.0):
    """Improve a ratio-greedy cache with bounded 1-for-1 and 1-for-2 exchanges."""
    if not chosen or candidate_videos.size == 0:
        return chosen

    candidate_sizes = sizes[candidate_videos]
    ratios = values / np.power(candidate_sizes, alpha)
    ratio_order = np.argsort(-ratios)

    # Pair searches use a bounded pool; one-for-one replacements still scan all candidates.
    pair_pool = np.unique(np.concatenate((
        ratio_order[:32],
        np.argsort(candidate_sizes)[:32],
    )))

    chosen_set = set(chosen)
    used_capacity = sum(int(sizes[video_id]) for video_id in chosen_set)
    original_chosen = list(chosen)

    for removed_video in original_chosen:
        if removed_video not in chosen_set:
            continue

        removed_index = np.searchsorted(candidate_videos, removed_video)
        available = capacity - used_capacity + int(sizes[removed_video])
        selected_ids = np.fromiter(chosen_set, dtype=np.int64, count=len(chosen_set))
        unselected = ~np.isin(candidate_videos, selected_ids)
        eligible = unselected & (candidate_sizes <= available)

        best_value = 0.0
        best_additions = []
        eligible_indices = np.flatnonzero(eligible)
        if eligible_indices.size:
            best_index = eligible_indices[np.argmax(values[eligible_indices])]
            best_value = float(values[best_index])
            best_additions = [int(candidate_videos[best_index])]

        pair_indices = pair_pool[~np.isin(candidate_videos[pair_pool], selected_ids)]
        if pair_indices.size >= 2:
            pair_sizes = candidate_sizes[pair_indices]
            pair_values = values[pair_indices]
            feasible_pairs = np.triu(
                pair_sizes[:, None] + pair_sizes[None, :] <= available,
                k=1,
            )
            if feasible_pairs.any():
                pair_scores = pair_values[:, None] + pair_values[None, :]
                pair_scores[~feasible_pairs] = -np.inf
                first, second = np.unravel_index(np.argmax(pair_scores), pair_scores.shape)
                pair_value = float(pair_scores[first, second])
                if pair_value > best_value:
                    best_value = pair_value
                    best_additions = [
                        int(candidate_videos[pair_indices[first]]),
                        int(candidate_videos[pair_indices[second]]),
                    ]

        if best_value <= float(values[removed_index]) + 1e-9:
            continue

        chosen_set.remove(removed_video)
        used_capacity -= int(sizes[removed_video])
        for video_id in best_additions:
            chosen_set.add(video_id)
            used_capacity += int(sizes[video_id])

        for candidate_index in ratio_order:
            video_id = int(candidate_videos[candidate_index])
            video_size = int(sizes[video_id])
            if video_id not in chosen_set and video_size <= capacity - used_capacity:
                chosen_set.add(video_id)
                used_capacity += video_size

    return list(chosen_set)


def ReoptimizeCache(cache_id, data, structures, S_np, V, output, alpha=1.0):
    """
    Réoptimise ENTIÈREMENT le contenu d'un cache, en tenant compte de
    l'état ACTUEL (final) de tous les autres caches
    """
    X = data["X"]
    old_videos = list(output[cache_id])

    total_delta = 0.0
    for v in old_videos:
        total_delta += RemoveVideo(v, cache_id, structures)

    candidate_videos, values = ComputeLocalCandidates(cache_id, structures, V)
    new_videos = []
    if candidate_videos.size > 0:
        sizes = S_np[candidate_videos]
        ratios = values / np.power(sizes, alpha)
        order = np.argsort(-ratios)
        capacity = X
        for idx in order:
            v = int(candidate_videos[idx])
            size = data["S"][v]
            if size <= capacity:
                capacity -= size
                new_videos.append(v)

        new_videos = ImproveByExchanges(
            new_videos,
            candidate_videos,
            values,
            S_np,
            X,
            alpha=alpha,
        )
        for v in new_videos:
            total_delta += AddVideo(v, cache_id, structures)

    if total_delta < -1e-6:
        # Sécurité anti-régression : on annule et on restaure l'ancien contenu.
        for v in new_videos:
            RemoveVideo(v, cache_id, structures)
        for v in old_videos:
            AddVideo(v, cache_id, structures)
        output[cache_id] = set(old_videos)
        return 0.0

    output[cache_id] = set(new_videos)
    return max(total_delta, 0.0)


def InitializeFromGreedy(data, structures, output, verbose=True, alpha=1.0):
    """
    Lance une première passe Greedy_Ratio et rejoue son placement des vidéos
    dans les caches pour initialiser `structures` (best_latency_arr,
    providers) et `output`, au lieu de partir de caches vides (LD partout).
    """
    if verbose:
        print("[Init] Première passe Greedy_Ratio...")

    t0 = time.time()
    greedy_result = Greedy(data, alpha=alpha)
    for cache_id, videos in greedy_result["output"].items():
        output[cache_id] = set(videos)
        for video_id in videos:
            AddVideo(video_id, cache_id, structures)

    if verbose:
        nb_placements = sum(len(v) for v in output.values())
        print(f"[Init] Terminé en {time.time() - t0:.1f}s")
        print(f"[Init]   chrono = {greedy_result['chrono']:,.0f} ms | score = {greedy_result['score']:,}")
        print(f"[Init]   {nb_placements:,} placements vidéo/cache")


def LocalSearch(data, max_rounds=10, time_budget_seconds=120, verbose=True, alpha=1.0, trace=False):
    """
    à chaque round, on réoptimise chaque cache,
    un par un, en tenant compte de l'état réel (final) des autres caches.
    On s'arrête si le score n'augmente plus (convergence) ou si le budget
    de temps est dépassé.
    La solution de départ est le résultat d'une première passe Greedy_Ratio.
    Si trace=True, les modifications nettes de chaque cache sont écrites
    dans outputs/<instance>.trace (la solution initiale Greedy n'y figure pas).
    """
    trace_lines = [] if trace else None
    try:
        return _LocalSearch(data, max_rounds, time_budget_seconds, verbose, alpha, trace_lines)
    finally:
        if trace:
            WriteTrace(trace_lines, Path("outputs") / f"{data.get('name', 'solution')}.trace")


def _LocalSearch(data, max_rounds, time_budget_seconds, verbose, alpha, trace_lines):
    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError("alpha doit être un nombre fini positif ou nul.")

    V, C = data["V"], data["C"]
    S_np = np.array(data["S"], dtype=np.float64)

    if verbose:
        print("[Prep] Précalcul des structures...")
    t0 = time.time()
    structures = PrecomputeStructures(data)
    if verbose:
        print(f"[Prep] Terminé en {time.time() - t0:.1f}s")
        print(SUB)

    output = {c: set() for c in range(C)}
    InitializeFromGreedy(data, structures, output, verbose=verbose, alpha=alpha)

    if verbose:
        print(SUB)
        budget_str = f"{time_budget_seconds}s" if time_budget_seconds is not None else "illimité"
        print(f"[LS] Recherche locale | max_rounds = {max_rounds} | budget = {budget_str} | alpha = {alpha}")
        print(SUB)

    # Points de suivi intra-round (25 %, 50 %, 75 %)
    checkpoints = {max(1, (C * q) // 4) - 1: q * 25 for q in (1, 2, 3)} if C >= 8 else {}

    start = time.time()
    total_gain = 0.0

    for round_idx in range(1, max_rounds + 1):
        round_gain = 0.0
        improved_caches = 0
        for cache_id in range(C):
            cache_gain = ReoptimizeCache(cache_id, data, structures, S_np, V, output, alpha=alpha)
            round_gain += cache_gain
            if cache_gain > 1e-6:
                improved_caches += 1

            if verbose and cache_id in checkpoints:
                print(f"[LS] Round {round_idx:>2} | {checkpoints[cache_id]:>3}% "
                      f"| gain partiel = {round_gain:>14,.0f} ms | t = {time.time() - start:6.1f}s")
        if trace_lines is not None:
            trace_lines.append(f"# round {round_idx}")
        for cache_id in range(C):
            old_videos = set(output[cache_id]) if trace_lines is not None else None
            round_gain += ReoptimizeCache(cache_id, data, structures, S_np, V, output, alpha=alpha)

            if trace_lines is not None:
                # Diff net : retraits d'abord, pour que la capacité reste valide au rejeu.
                new_videos = output[cache_id]
                for v in sorted(old_videos - new_videos):
                    trace_lines.append(f"- {cache_id} {v}")
                for v in sorted(new_videos - old_videos):
                    trace_lines.append(f"+ {cache_id} {v}")

            if time_budget_seconds is not None and (time.time() - start) > time_budget_seconds:
                if verbose:
                    total_gain += round_gain
                    print(f"[LS] Budget de temps atteint (round {round_idx}, cache {cache_id + 1}/{C}).")
                    print(SUB)
                    print(f"[LS] Bilan : {round_idx - 1} round(s) complet(s) "
                          f"| gain total = {total_gain:,.0f} ms | t = {time.time() - start:.1f}s")
                    print(SEP)
                return output

        total_gain += round_gain
        if verbose:
            elapsed = time.time() - start
            print(f"[LS] Round {round_idx:>2} | 100% | gain round   = {round_gain:>14,.0f} ms "
                  f"| caches améliorés = {improved_caches}/{C} | t = {elapsed:6.1f}s")

        if round_gain <= 1e-6:
            if verbose:
                print("[LS] Convergence atteinte : plus aucune amélioration possible.")
            break

    if verbose:
        print(SUB)
        print(f"[LS] Bilan : {round_idx} round(s) | gain total = {total_gain:,.0f} ms "
              f"| t = {time.time() - start:.1f}s")
        print(SEP)

    return output

def FinalScore(data, output):
    endpoints_by_id = data["endpoints"]
    chrono = 0
    total_requests = 0

    for endpoint_id, requests in data["requests"].items():
        endpoint = endpoints_by_id[endpoint_id]
        LD = endpoint["data_center_latency"]
        for video_id, num_requests in requests.items():
            total_requests += num_requests

            best_latency = LD
            for cache_id, latency in endpoint["cache_connections"]:
                if video_id in output[cache_id]:
                    best_latency = latency
                    break

            chrono += num_requests * (LD - best_latency)

    score = (chrono * 1000) // total_requests if total_requests > 0 else 0
    return chrono, score


if __name__ == "__main__":
    t_global = time.time()

    if len(sys.argv) > 1:
        data = Main(sys.argv[1])
    else:
        data = Main()

    output = LocalSearch(data, max_rounds=10, time_budget_seconds=120, verbose=True, alpha=1.0)
def WriteOutput(output, out_path):
    """Écrit la solution au format .out : nombre de caches utilisés, puis une ligne 'cache_id v1 v2 ...' par cache non vide."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    output_lists = {
        cache_id: sorted(videos)
        for cache_id, videos in output.items()
        if videos
    }

    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"{len(output_lists)}\n")
        for c_id, videos in output_lists.items():
            f.write(" ".join(map(str, (c_id, *videos))) + "\n")

    print(f"Solution écrite dans : {out_path}")
    return output_lists


def WriteTrace(trace_lines, trace_path):
    """Écrit la trace : '# round N' puis des lignes '+ cache video' / '- cache video'."""
    trace_path = Path(trace_path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as f:
        for line in trace_lines:
            f.write(line + "\n")
    print(f"Trace écrite dans : {trace_path}")


if __name__ == "__main__":
    data = Main()

    output = LocalSearch(data, max_rounds=10, time_budget_seconds=120, verbose=True, alpha=1.0, trace=True)

    out_path = Path("outputs") / f"{data['name']}.out"
    WriteOutput(output, out_path)

    chrono, score = FinalScore(data, output)
    print("[Résultat]")
    print(f"   Caches utilisés         : {len(output_lists):,}/{data['C']:,}")
    print(f"   Chrono (gain total, ms) : {chrono:,}")
    print(f"   Score (gain moyen, µs)  : {score:,}")
    print(f"   Temps total             : {time.time() - t_global:.1f}s")
    print(SEP)
