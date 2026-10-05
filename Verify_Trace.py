from pathlib import Path

from Greedy_Ratio import Greedy
from Local_Search import Main, FinalScore


def ReadOutput(out_path, data):
    """Lit un fichier .out et vérifie son format (ids valides, capacité respectée)."""
    out_path = Path(out_path)
    with out_path.open("r", encoding="utf-8") as f:
        lines = [line.split() for line in f if line.strip()]

    if not lines:
        raise ValueError(f"{out_path} : fichier vide.")

    N = int(lines[0][0])
    if N != len(lines) - 1:
        raise ValueError(f"{out_path} : {N} caches annoncés mais {len(lines) - 1} lignes trouvées.")

    output = {c: set() for c in range(data["C"])}
    seen = set()
    for line in lines[1:]:
        cache_id, *videos = map(int, line)
        if not 0 <= cache_id < data["C"]:
            raise ValueError(f"{out_path} : cache {cache_id} hors limites.")
        if cache_id in seen:
            raise ValueError(f"{out_path} : cache {cache_id} décrit plusieurs fois.")
        seen.add(cache_id)

        for v in videos:
            if not 0 <= v < data["V"]:
                raise ValueError(f"{out_path} : vidéo {v} hors limites (cache {cache_id}).")
        output[cache_id] = set(videos)

        used = sum(data["S"][v] for v in output[cache_id])
        if used > data["X"]:
            raise ValueError(f"{out_path} : cache {cache_id} dépasse la capacité ({used} > {data['X']}).")

    return output


def ReplayTrace(trace_path, data, alpha=1.0):
    """
    Part de la solution Greedy_Ratio (la même que celle utilisée par LocalSearch)
    et rejoue la trace en vérifiant chaque opération.
    """
    greedy_result = Greedy(data, alpha=alpha)
    state = {c: set() for c in range(data["C"])}
    for cache_id, videos in greedy_result["output"].items():
        state[cache_id] = set(videos)
    used = {c: sum(data["S"][v] for v in state[c]) for c in state}

    trace_path = Path(trace_path)
    with trace_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) != 3 or parts[0] not in ("+", "-"):
                raise ValueError(f"{trace_path}:{line_no} : ligne invalide '{line}'.")
            op, cache_id, video_id = parts[0], int(parts[1]), int(parts[2])

            if not 0 <= cache_id < data["C"] or not 0 <= video_id < data["V"]:
                raise ValueError(f"{trace_path}:{line_no} : cache ou vidéo hors limites.")

            if op == "+":
                if video_id in state[cache_id]:
                    raise ValueError(f"{trace_path}:{line_no} : vidéo {video_id} déjà dans le cache {cache_id}.")
                state[cache_id].add(video_id)
                used[cache_id] += data["S"][video_id]
                if used[cache_id] > data["X"]:
                    raise ValueError(f"{trace_path}:{line_no} : capacité du cache {cache_id} dépassée "
                                     f"({used[cache_id]} > {data['X']}).")
            else:
                if video_id not in state[cache_id]:
                    raise ValueError(f"{trace_path}:{line_no} : vidéo {video_id} absente du cache {cache_id}.")
                state[cache_id].remove(video_id)
                used[cache_id] -= data["S"][video_id]

    return state


def Verify(filename=None, alpha=1.0):
    # Sans filename, on utilise l'instance par défaut de Local_Search.Main
    data = Main() if filename is None else Main(filename)
    out_path = Path("outputs") / f"{data['name']}.out"
    trace_path = Path("outputs") / f"{data['name']}.trace"

    output = ReadOutput(out_path, data)
    print(f"{out_path} : format valide.")

    replayed = ReplayTrace(trace_path, data, alpha=alpha)
    print(f"{trace_path} : rejouée sans erreur.")

    diff = [c for c in range(data["C"]) if replayed[c] != output[c]]
    if diff:
        print(f"ÉCHEC : la trace rejouée diffère du .out sur {len(diff)} cache(s) : {diff[:10]}")
        return False

    chrono, score = FinalScore(data, output)
    print("OK : la trace rejouée depuis Greedy_Ratio redonne exactement le .out.")
    print(f"Score (gain moyen, µs)  : {score}")
    return True


if __name__ == "__main__":
    # alpha doit être le même que celui passé à LocalSearch
    Verify(alpha=1.0)
