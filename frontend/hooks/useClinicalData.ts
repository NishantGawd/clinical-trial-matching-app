"use client";

import { useCallback, useEffect, useState } from "react";
import { listPatients, listTrials, ApiRequestError } from "@/lib/api";
import type { Patient, Trial } from "@/types/clinical";

interface ListState<T> {
  items: T[];
  count: number;
  loading: boolean;
  error: string | null;
}

export function usePatients(limit = 50) {
  const [state, setState] = useState<ListState<Patient>>({
    items: [],
    count: 0,
    loading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await listPatients({ limit });
      setState({ items: res.patients, count: res.count, loading: false, error: null });
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "Failed to load patients.";
      setState({ items: [], count: 0, loading: false, error: message });
    }
  }, [limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}

export function useTrials(limit = 50) {
  const [state, setState] = useState<ListState<Trial>>({
    items: [],
    count: 0,
    loading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await listTrials({ limit });
      setState({ items: res.trials, count: res.count, loading: false, error: null });
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "Failed to load trials.";
      setState({ items: [], count: 0, loading: false, error: message });
    }
  }, [limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}
