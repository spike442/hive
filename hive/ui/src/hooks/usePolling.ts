import { useEffect, useRef } from "react";

export function usePolling(
  key: string,
  refreshKey: number,
  refresh: (signal: AbortSignal) => Promise<void>,
) {
  const callback = useRef(refresh);
  useEffect(() => {
    callback.current = refresh;
  });
  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    let timer: number | undefined;
    async function poll() {
      try {
        await callback.current(controller.signal);
      } finally {
        if (!controller.signal.aborted)
          timer = window.setTimeout(() => void poll(), 5000);
      }
    }
    void poll();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [key, refreshKey]);
}
