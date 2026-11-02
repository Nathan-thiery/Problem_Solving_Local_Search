import sys
from pathlib import Path
import numpy as np


def Main(filename: str = "./videos_worth_spreading.in"):
    candidates = [
        Path("instances") / filename,
        Path(filename),
    ]

    for path in candidates:
        if path.exists():
            print(f"Lecture du fichier : {path}")
            with path.open("r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line:
                    raise ValueError(f"Le fichier {path} est vide.")

                values = list(map(int, first_line.split()))
                if len(values) < 5:
                    raise ValueError(f"Le fichier {path} ne contient pas assez d'entiers sur la première ligne.")

                # On récupère les 5 premiers entiers de la première ligne après l'ouverture du fichier
                V, E, R, C, X = values[:5]

                # On lit la deuxième ligne pour obtenir les tailles des vidéos
                S = list(map(int, f.readline().strip().split()))
                if len(S) < V:
                    raise ValueError(f"Le fichier {path} ne contient pas assez de tailles de vidéos.")

                # On lit les informations des endpoints
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
                    # Tri par latence croissante déplacé en dehors de la boucle interne
                    cache_connections = sorted(cache_connections.items(), key=lambda item: item[1])

                    endpoints.append({
                        "id": endpoint_id,
                        "data_center_latency": LD,
                        "cache_connections": cache_connections,
                    })

                # Section 4 : Requêtes
                Requests = {}
                for _ in range(R):
                    line = f.readline().strip().split()
                    if len(line) < 3:
                        raise ValueError("Ligne de requête incomplète.")
                    v, e, n = map(int, line)
                    endpoint_requests = Requests.setdefault(e, {})
                    endpoint_requests[v] = endpoint_requests.get(v, 0) + n

                return {
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


def BuildValueMatrix(data):
    """
    Calcule, pour chaque paire (vidéo, cache), la valeur BRUTE de placer
    cette vidéo dans ce cache (somme, sur tous les endpoints connectés à ce
    cache et demandant cette vidéo, du gain de latence potentiel en fonction du
    nombre de requêtes, PAR RAPPORT AU DATA CENTER) :
    Renvoi une matrice qui sert à décider dans quel ORDRE traiter les caches ensuite
    """
    V, C = data["V"], data["C"]
    value_matrix = np.zeros((V, C), dtype=np.float64)

    for endpoint_id, requests in data["requests"].items():
        endpoint = data["endpoints"][endpoint_id]
        cache_connections = endpoint["cache_connections"]
        if not requests or not cache_connections:
            continue

        LD = endpoint["data_center_latency"]

        video_ids = np.fromiter(requests.keys(), dtype=np.int64, count=len(requests))
        counts = np.fromiter(requests.values(), dtype=np.float64, count=len(requests))

        cache_ids = np.fromiter((c for c, _l in cache_connections), dtype=np.int64, count=len(cache_connections))
        latencies = np.fromiter((l for _c, l in cache_connections), dtype=np.float64, count=len(cache_connections))
        gains = LD - latencies

        contribution = np.outer(counts, gains)
        value_matrix[np.ix_(video_ids, cache_ids)] += contribution

    return value_matrix


def PrecomputeEndpointArrays(data):
    """
    Pré-calcule, pour chaque endpoint, des tableaux numpy alignés :
      - video_ids_arr[e]  : IDs des vidéos demandées par l'endpoint e
      - counts_arr[e]     : nombre de requêtes associées
      - best_latency_arr[e] : la MEILLEURE latence actuellement accessible
        pour chacune de ces vidéos (initialisée à LD_e = data center, mise
        à jour au fil du placement des vidéos dans les caches connectés).
    """
    E = data["E"]
    video_ids_arr = [None] * E
    counts_arr = [None] * E
    best_latency_arr = [None] * E

    for endpoint_id in range(E):
        requests = data["requests"].get(endpoint_id, {})
        LD = data["endpoints"][endpoint_id]["data_center_latency"]
        if requests:
            # Id de chaque videos demand&es par l'endpoint
            v_ids = np.fromiter(requests.keys(), dtype=np.int64, count=len(requests))
            # Nombre de requêtes associées à chaque vidéos
            counts = np.fromiter(requests.values(), dtype=np.float64, count=len(requests))
        else:
            v_ids = np.empty(0, dtype=np.int64)
            counts = np.empty(0, dtype=np.float64)
        video_ids_arr[endpoint_id] = v_ids
        counts_arr[endpoint_id] = counts
        best_latency_arr[endpoint_id] = np.full(v_ids.shape[0], LD, dtype=np.float64)

    return video_ids_arr, counts_arr, best_latency_arr


def Greedy(data, alpha=1.0):
    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError("alpha doit être un nombre fini positif ou nul.")

    V, C, X = data["V"], data["C"], data["X"]
    S = data["S"]
    S_np = np.array(S, dtype=np.float64)

    # Mise à plat des requêtes, en conservant l'endpoint d'origine
    Request_flat = []
    for endpoint_id, requests in data["requests"].items():
        for video_id, num_requests in requests.items():
            Request_flat.append({
                "video_id": video_id,
                "endpoint_id": endpoint_id,
                "num_requests": num_requests,
            })

    # calcule d'une matrice d'importance des caches
    value_matrix = BuildValueMatrix(data)
    cache_order = np.argsort(-value_matrix.sum(axis=0))

    # reverse_conn[c] = liste des (endpoint_id, latence) connectés au cache c
    reverse_conn = {c: [] for c in range(C)}
    for endpoint in data["endpoints"]:
        for cache_id, latency in endpoint["cache_connections"]:
            reverse_conn[cache_id].append((endpoint["id"], latency))

    video_ids_arr, counts_arr, best_latency_arr = PrecomputeEndpointArrays(data)

    output = {cache_id: set() for cache_id in range(C)}


    for cache_id in cache_order.tolist():
        connections = reverse_conn[cache_id]
        if not connections:
            continue

        # Calcul du gain par vidéo pour CE cache, en tenant compte
        #de la meilleure latence déjà accessible pour chaque endpoint
        #connecté (via d'autres caches déjà traités).
        local_value = np.zeros(V, dtype=np.float64)
        for endpoint_id, Lc in connections:
            v_ids = video_ids_arr[endpoint_id]
            if v_ids.size == 0:
                continue
            best = best_latency_arr[endpoint_id]
            marginal_gain = np.maximum(0.0, best - Lc) * counts_arr[endpoint_id]
            local_value[v_ids] += marginal_gain

        candidate_videos = np.nonzero(local_value)[0] # tableau des indices des vidéos qui ont une valeur non nulle (gain à mettre en cache)
        if candidate_videos.size == 0:
            continue

        # Ratio (gain marginal x nb requêtes) / taille de la vidéo,
        # trié décroissant : on remplit ce cache par ordre de rentabilité
        # par Mo de capacité consommée.
        values = local_value[candidate_videos]  # valeurs des vidéos de gain nn-nulles
        sizes = S_np[candidate_videos]          # taille des vidéos de gain nn-nulles
        ratios = values / np.power(sizes, alpha)
        order = np.argsort(-ratios)

        capacity = X
        chosen = []
        for idx in order:
            v = int(candidate_videos[idx])
            size = S[v]
            if size <= capacity:
                capacity -= size
                chosen.append(v)
                output[cache_id].add(v)

        # Mise à jour de la meilleure latence accessible pour les
        # endpoints connectés à ce cache, pour les vidéos qui viennent
        # d'y être placées.
        if chosen:
            chosen_arr = np.array(chosen, dtype=np.int64)
            for endpoint_id, Lc in connections:
                v_ids = video_ids_arr[endpoint_id]
                if v_ids.size == 0:
                    continue
                mask = np.isin(v_ids, chosen_arr)
                if mask.any():
                    best = best_latency_arr[endpoint_id]
                    best[mask] = np.minimum(best[mask], Lc)

    # On reparcourt les requêtes en utilisant les caches, pour chaque requête, L = min(LD, latences des
    # caches connectés à l'endpoint ET contenant la vidéo).
    chrono = 0  # somme des gains (ms), pondérée : somme(Rn * (LD - L))
    total_requests = 0

    # Accès direct aux endpoints par index : endpoints[i]["id"]
    endpoints_by_id = data["endpoints"]

    for req in Request_flat:
        video_id = req["video_id"]
        endpoint_id = req["endpoint_id"]
        num_requests = req["num_requests"]
        total_requests += num_requests

        endpoint = endpoints_by_id[endpoint_id]
        LD = endpoint["data_center_latency"]

        best_latency = LD  # par défaut
        for cache_id, latency in endpoint["cache_connections"]:
            if video_id in output[cache_id]:
                best_latency = latency  # premier match = le plus faible (tri croissant)
                break

        chrono += num_requests * (LD - best_latency)

    # somme des gains (ms) * 1000 / nombre total de requêtes, arrondi vers le bas
    score = (chrono * 1000) // total_requests if total_requests > 0 else 0

    # Conversion des sets en listes pour la sortie, en filtrant les caches vides
    output_lists = {
        cache_id: list(videos_id)
        for cache_id, videos_id in output.items()
        if videos_id
    }

    return {
        "output": output_lists,
        "chrono": chrono,
        "score": score,
    }


if __name__ == "__main__":
    data = Main()
    outputs = Greedy(data)
    print(len(outputs["output"]))
    # Iterate over the keys of the output dictionary, which are cache_ids
    for c_id in outputs["output"]:
        print(c_id, *outputs["output"][c_id])
    print(f"Chrono (gain total, ms) : {outputs['chrono']}")
    print(f"Score (gain moyen, µs)  : {outputs['score']}")