import { useRef, useMemo } from "react";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import type { CheckResponse } from "../types/api";
import { useAppStore } from "../store/appStore";

export function useGrammarCheck() {
  const abortRef = useRef<AbortController | null>(null);
  const setResult = useAppStore((s) => s.setResult);
  const setSubmitState = useAppStore((s) => s.setSubmitState);
  const setErrorMessage = useAppStore((s) => s.setErrorMessage);

  const mutation = useMutation({
    mutationFn: async (text: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const { data } = await axios.post<CheckResponse>("/check", { text }, {
        signal: controller.signal,
      });
      return data;
    },
    onMutate: () => {
      setSubmitState("loading");
      setErrorMessage(null);
    },
    onSuccess: (data) => {
      setResult(data);
      setSubmitState("success");
    },
    onError: (err: Error) => {
      if (axios.isCancel(err)) return;
      setErrorMessage(err.message || "Check failed. Is the backend running?");
      setSubmitState("error");
    },
  });

  const cancel = useMemo(() => () => {
    abortRef.current?.abort();
    setSubmitState("idle");
  }, [setSubmitState]);

  return { ...mutation, cancel };
}
