import instanceCreator as ic

#### PARSER
def instanceValidator() -> bool:
    # Première ligne
    # V: Nombre de vidéo
    # E: Nombre d'endpoint
    # R: Nombre de requêtes
    # C: Nombre de cache
    # X: Taille du cache (Mo)
    V, E, R, C, X = map(int, input().split())
    
    # Verification
    assert 1 <= V <= ic.MAX_AUTHORISED_VIDEO_NUMBER, "Maximum number of video exceeded or negative."
    assert 1 <= E <= ic.MAX_AUTHORISED_ENDPOINT_NUMBER, "Maximum number of endpoint exceeded or negative."
    assert 1 <= R <= ic.MAX_AUTHORISED_REQUEST_NUMBER, "Maximum number of requests exceeded or negative."
    assert 1 <= C <= ic.MAX_AUTHORISED_CACHE_NUMBER, "Maximum number of cache exceeded or negative"
    assert 1 <= X <= ic.MAX_AUTHORISED_CACHE_CAPACITY, "Maximum cache capacity exceeded or negative"
    
    # Taille des vidéos
    video_sizes = list(map(int, input().split()))
    
    # Verification
    for v in video_sizes:
        assert 1 <= v <= ic.MAX_AUTHORISED_VIDEO_SIZE, "Maximum video size exceeded or negative"

    # Endpoints
    for _ in range(E):
        # Latence du centre de données et nombre de cache connecté
        latency_dc, K = map(int, input().split())
        
        # Verification
        assert ic.MIN_AUTHORISED_SERVER_LATENCY <= latency_dc <= ic.MAX_AUTHORISED_SERVER_LATENCY, "Maximum or Minimum Data Center Latency not respected."

        # Caches
        for _ in range(K):
            # Latence pour atteindre le cache
            cache_id, latency = map(int, input().split())
            
            # Verification
            assert 1 <= latency <= ic.MAX_AUTHORISED_CACHE_LATENCY, "Maximum cache latency exceeded or negative"
            assert latency < latency_dc, "Cache Latency greater or equal to server latency."

    # Get each requests
    requestsPerEndpoint = [0 for i in range(E)]
    for _ in range(R):
        video, endpoint, count = map(int, input().split())
        requestsPerEndpoint[endpoint] += 1
        
        # Verification
        assert requestsPerEndpoint[endpoint] <= ic.MAX_AUTHORISED_REQUEST_PER_ENDPOINT, "Maximum number of request per endpoint exceeded"
            

    # Return all informations
    return True

#### MAIN
if __name__ == "__main__":
    # Notice for usage: run then copy-paste instance. You may need to press enter.
    try:
        if instanceValidator():
            print("VALID INSTANCE")
    except Exception as e:
        while(input()!=""):
            continue
        print(f"INVALID INSTANCE: {e}\nPRESS ENTER TO EXIT.")
