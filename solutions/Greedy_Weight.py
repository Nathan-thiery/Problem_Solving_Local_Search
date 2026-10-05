import sys
from pathlib import Path


def Main(filename: str = "./kittens.in"):
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

                print(f"Somme des tailles des vidéos : {sum(S)}")

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
                    Requests.setdefault(e, []).append({
                        "video_id": v,
                        "num_requests": n
                    })

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


def Eval(Request, videos_by_weight):
    # On trie une copie de la liste des requêtes, sans modifier la liste d'origine.
    # Le critère est le poids de la vidéo demandée (score associé au video_id).
    Tab_Requests_Order = sorted(
        Request.copy(),
        key=lambda req: videos_by_weight.get(req["video_id"], 0),
        reverse=True,
    )
    return Tab_Requests_Order


def Greedy(data):
    # Comptage par cache pour garder l'identifiant du cache lors du tri
    Tab_C = {}
    for endpoint in data["endpoints"]:
        for cache_id, _latency in endpoint["cache_connections"]:
            Tab_C[cache_id] = Tab_C.setdefault(cache_id, 0) + 1

    # Comptage par vidéo pour garder l'identifiant de la vidéo lors du tri
    Tab_V = {}
    for endpoint_id, requests in data["requests"].items():
        for req in requests:
            video_id = req["video_id"]
            Tab_V[video_id] = Tab_V.setdefault(video_id, 0) + 1

    # Poids des vidéos = nombre de requêtes * taille de la vidéo
    Tab_V_poids = {}
    for video_id, nb_requests in Tab_V.items():
        Tab_V_poids[video_id] = nb_requests * data["S"][video_id]

    # Tri décroissant en gardant les identifiants associés
    caches_by_popularity = sorted(Tab_C.items(), key=lambda item: item[1], reverse=True)
    videos_by_popularity = sorted(Tab_V.items(), key=lambda item: item[1], reverse=True)
    videos_by_weight = sorted(Tab_V_poids.items(), key=lambda item: item[1], reverse=True)

    # Mise à plat des requêtes, en conservant l'endpoint d'origine
    Request_flat = []
    for endpoint_id, requests in data["requests"].items():
        for req in requests:
            Request_flat.append({
                "video_id": req["video_id"],
                "endpoint_id": endpoint_id,
                "num_requests": req["num_requests"],
            })

    Request_order = Eval(Request_flat, dict(videos_by_weight))

    output = {cache_id: set() for cache_id in range(data["C"])}
    cache_capacity_available = [data["X"] for _ in range(data["C"])]

    # Accès aux endpoints par index (endpoints[i]["id"])
    endpoints_by_id = data["endpoints"]

    # On décide où placer les vidéos
    for req in Request_order:
        video_id = req["video_id"]
        endpoint_id = req["endpoint_id"]
        endpoint = endpoints_by_id[endpoint_id]

        # Vidéo déjà présente dans un des caches connectés à cet endpoint ?
        already_cached = any(
            video_id in output[cache_id]
            for cache_id, _latency in endpoint["cache_connections"]
        )

        # Si pas déjà en cache pour cet endpoint, on tente de la placer dans le cache le plus proche qui a la capacité disponible.
        if not already_cached:
            for cache_id, _latency in endpoint["cache_connections"]:
                if data["S"][video_id] <= cache_capacity_available[cache_id]:
                    cache_capacity_available[cache_id] -= data["S"][video_id]
                    output[cache_id].add(video_id)
                    break


    # Calcul du score en regardant les caches : L = min(LD, latences des caches connectés à l'endpoint ET contenant la vidéo).
    chrono = 0  # somme des gains (ms), pondérée : somme(Rn * (LD - L))
    total_requests = 0

    for req in Request_flat:
        video_id = req["video_id"]
        endpoint_id = req["endpoint_id"]
        num_requests = req["num_requests"]
        total_requests += num_requests

        endpoint = endpoints_by_id[endpoint_id]
        LD = endpoint["data_center_latency"]

        best_latency = LD  # par défaut
        # parcours des caches de l'endpoint
        for cache_id, latency in endpoint["cache_connections"]:
            # quel cache contient la video (si aucun LD défaut)
            if video_id in output[cache_id]:
                best_latency = latency
                break

        chrono += num_requests * (LD - best_latency)

    # somme des gains (ms) * 1000 / nombre total de requêtes, arrondi vers le bas
    score = (chrono * 1000) // total_requests if total_requests > 0 else 0

    # Conversion des sets en listes pour la sortie
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

    for c_id in outputs["output"]:
        print(c_id, *outputs["output"][c_id])
    print(f"Chrono (gain total, ms) : {outputs['chrono']}")
    print(f"Score (gain moyen, µs)  : {outputs['score']}")