import { useCallback, useEffect, useRef, useState } from "react";
import { api, parseApiError } from "@/services/api";

/** Small data-fetching hook: GET a resource, expose loading/error and a reload function. */
export function useApi<T>(url: string | null, params?: Record<string, unknown>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(!!url);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | undefined>();
  const key = JSON.stringify(params ?? {});
  const seq = useRef(0);

  const load = useCallback(async () => {
    if (!url) return;
    const id = ++seq.current;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<T>(url, { params: params ?? undefined, paramsSerializer: { indexes: null } });
      if (id === seq.current) setData(data);
    } catch (e) {
      if (id === seq.current) {
        const info = parseApiError(e, "Could not load this information.");
        setError(info.message);
        setStatus(info.status);
      }
    } finally {
      if (id === seq.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, key]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, setData, loading, error, status, reload: load };
}

export function useDebounced<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}
