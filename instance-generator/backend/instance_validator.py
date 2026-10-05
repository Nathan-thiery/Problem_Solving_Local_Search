from __future__ import annotations


MAX_VIDEO_NUMBER = 10000
MAX_VIDEO_SIZE = 1000
MAX_CACHE_NUMBER = 1000
MAX_CACHE_CAPACITY = 500000
MAX_CACHE_LATENCY = 500
MIN_DATACENTER_LATENCY = 2
MAX_DATACENTER_LATENCY = 4000
MAX_REQUEST_DESCRIPTIONS = 1000000
MAX_REQUESTS_PER_ENDPOINT = 10000


def validate_instance(instance: str) -> tuple[bool, str | None]:
    """Validate an instance using the rules from instance-validator."""
    try:
        lines = instance.splitlines()
        if len(lines) < 2:
            raise ValueError("fichier incomplet")

        header = _parse_line(lines[0], 5, "en-tete")
        video_count, endpoint_count, request_count, cache_count, cache_capacity = header
        _check_range(video_count, 1, MAX_VIDEO_NUMBER, "nombre de videos")
        _check_range(endpoint_count, 1, 1000, "nombre d'endpoints")
        _check_range(request_count, 1, MAX_REQUEST_DESCRIPTIONS, "nombre de descriptions de requetes")
        _check_range(cache_count, 1, MAX_CACHE_NUMBER, "nombre de caches")
        _check_range(cache_capacity, 1, MAX_CACHE_CAPACITY, "capacite des caches")

        video_sizes = _parse_line(lines[1], video_count, "tailles des videos", exact=True)
        for size in video_sizes:
            _check_range(size, 1, MAX_VIDEO_SIZE, "taille video")

        line_index = 2
        request_descriptions_per_endpoint = [0] * endpoint_count
        for endpoint_id in range(endpoint_count):
            if line_index >= len(lines):
                raise ValueError("description endpoint manquante")
            latency_dc, connected_cache_count = _parse_line(
                lines[line_index], 2, f"endpoint {endpoint_id}"
            )
            line_index += 1
            _check_range(latency_dc, MIN_DATACENTER_LATENCY, MAX_DATACENTER_LATENCY, "latence data center")
            _check_range(connected_cache_count, 0, cache_count, "nombre de connexions cache")

            for connection_id in range(connected_cache_count):
                if line_index >= len(lines):
                    raise ValueError("connexion cache manquante")
                cache_id, latency = _parse_line(
                    lines[line_index], 2, f"connexion {endpoint_id}/{connection_id}"
                )
                line_index += 1
                _check_range(cache_id, 0, cache_count - 1, "identifiant cache")
                _check_range(latency, 1, MAX_CACHE_LATENCY, "latence cache")
                if latency >= latency_dc:
                    raise ValueError("la latence cache doit etre inferieure a celle du data center")

        remaining_lines = lines[line_index:]
        if len(remaining_lines) != request_count:
            raise ValueError(
                f"nombre de descriptions de requetes incorrect: attendu {request_count}, recu {len(remaining_lines)}"
            )

        for request_id, line in enumerate(remaining_lines):
            video_id, endpoint_id, request_number = _parse_line(line, 3, f"requete {request_id}")
            _check_range(video_id, 0, video_count - 1, "identifiant video")
            _check_range(endpoint_id, 0, endpoint_count - 1, "identifiant endpoint")
            _check_range(request_number, 1, 10000, "nombre de demandes")
            request_descriptions_per_endpoint[endpoint_id] += 1
            if request_descriptions_per_endpoint[endpoint_id] > MAX_REQUESTS_PER_ENDPOINT:
                raise ValueError("trop de descriptions de requetes pour un endpoint")

        return True, None
    except (TypeError, ValueError) as error:
        return False, str(error)


def _parse_line(line: str, expected_count: int, label: str, exact: bool = False) -> list[int]:
    values = line.split()
    if (exact and len(values) != expected_count) or (not exact and len(values) != expected_count):
        raise ValueError(f"{label}: nombre de valeurs incorrect")
    try:
        return [int(value) for value in values]
    except ValueError as error:
        raise ValueError(f"{label}: valeur non entiere") from error


def _check_range(value: int, minimum: int, maximum: int, label: str) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} hors limites [{minimum}, {maximum}]")
