"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getHealth } from "@/lib/api";

export type HealthState = "checking" | "online" | "offline";

export function useHealthCheck(pollMs = 20_000) {
  const [state, setState] = useState<HealthState>("checking");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const mounted = useRef(true);

  const check = useCallback(async () => {
    try {
      await getHealth();
      if (mounted.current) {
        setState("online");
        setLastChecked(new Date());
      }
    } catch {
      if (mounted.current) {
        setState("offline");
        setLastChecked(new Date());
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    check();
    const id = setInterval(check, pollMs);
    return () => {
      mounted.current = false;
      clearInterval(id);
    };
  }, [check, pollMs]);

  return { state, lastChecked, refresh: check };
}
