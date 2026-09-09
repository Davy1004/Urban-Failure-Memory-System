/**
 * The one data-fetching hook. Deliberately small — there are four read-only
 * endpoints and no mutations, so a query library would be more machinery than
 * the problem has.
 *
 * It holds the previous value while refetching rather than dropping back to a
 * loading state, so a re-fetch does not flash a skeleton and shift the layout.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export interface AsyncState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  /** True while refetching with a previous value still on screen. */
  refreshing: boolean;
  reload: () => void;
}

export function useAsync<T>(
  fn: () => Promise<T>,
  deps: readonly unknown[],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [pending, setPending] = useState(true);
  const [nonce, setNonce] = useState(0);
  const hasData = useRef(false);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  useEffect(() => {
    let live = true;
    setPending(true);
    setError(null);
    run()
      .then((value) => {
        if (!live) return;
        hasData.current = true;
        setData(value);
      })
      .catch((err: unknown) => {
        if (!live) return;
        setData(null);
        hasData.current = false;
        setError(err instanceof Error ? err : new Error(String(err)));
      })
      .finally(() => {
        if (live) setPending(false);
      });
    return () => {
      live = false;
    };
  }, [run, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return {
    data,
    error,
    loading: pending && !hasData.current,
    refreshing: pending && hasData.current,
    reload,
  };
}
