import { useCallback, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

interface ApiRequestState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface UseApiRequestResult<T, Args extends unknown[]> extends ApiRequestState<T> {
  execute: (...args: Args) => Promise<T>;
  reset: () => void;
}

function useApiRequest<T, Args extends unknown[]>(
  requestFn: (...args: Args) => Promise<T>
): UseApiRequestResult<T, Args> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(
    async (...args: Args): Promise<T> => {
      setLoading(true);
      setError(null);
      try {
        const result = await requestFn(...args);
        setData(result);
        return result;
      } catch (err) {
        const normalizedError = err instanceof Error ? err : new Error(String(err));
        setError(normalizedError);
        throw normalizedError;
      } finally {
        setLoading(false);
      }
    },
    [requestFn]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, execute, reset };
}

async function getHelloWorld() {
  const response = await fetch(`${API_BASE_URL}/`);
  if (!response.ok) {
    throw new Error(`Erreur API (GET /) : ${response.status}`);
  }
  return response.json();
}

export function useGetHelloWorld() {
  return useApiRequest(getHelloWorld);
}

export interface CreateInstanceParams {
  videosNb: number;
  endpointsNb: number;
  cacheServersNb: number;
  requestNb: number;
  videoDistribution: number;
  density: number;
  cacheSaturation: number;
  latencyDistribution: number;
}

export type CreateInstanceResponse = Blob;

async function postCreateInstance(
  params: CreateInstanceParams
): Promise<CreateInstanceResponse> {
  const response = await fetch(`${API_BASE_URL}/instances`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`Erreur API (POST /) : ${response.status}`);
  }

  return response.blob();
}

export function useCreateInstance() {
  return useApiRequest(postCreateInstance);
}
