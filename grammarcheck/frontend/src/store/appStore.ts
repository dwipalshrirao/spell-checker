import { create } from "zustand";
import type { CheckResponse, CheckError } from "../types/api";
import { applySingleFix } from "../utils/applyFixes";

export type SubmitState = "idle" | "loading" | "success" | "error";

interface AppState {
  text: string;
  setText: (text: string) => void;
  submitState: SubmitState;
  setSubmitState: (state: SubmitState) => void;
  result: CheckResponse | null;
  setResult: (r: CheckResponse | null) => void;
  errorMessage: string | null;
  setErrorMessage: (msg: string | null) => void;
  clearResult: () => void;
  selectedError: CheckError | null;
  setSelectedError: (e: CheckError | null) => void;
  applyFix: (index: number) => void;
  applyAllFixes: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  text: "",
  setText: (text) => set({ text }),
  submitState: "idle",
  setSubmitState: (submitState) => set({ submitState }),
  result: null,
  setResult: (result) => set({ result }),
  errorMessage: null,
  setErrorMessage: (errorMessage) => set({ errorMessage }),
  clearResult: () => set({ result: null, errorMessage: null, submitState: "idle" }),
  selectedError: null,
  setSelectedError: (selectedError) => set({ selectedError }),
  applyFix: (index) => {
    const { text, result, selectedError } = get();
    if (!result) return;
    const error = result.errors[index];
    if (!error) return;
    const { newText, found } = applySingleFix(text, error.original, error.corrected);
    if (!found) return;
    const newErrors = result.errors.filter((_, i) => i !== index);
    const newSelected = selectedError === error ? null : selectedError;
    set({
      text: newText,
      result: { ...result, errors: newErrors },
      selectedError: newSelected,
    });
  },
  applyAllFixes: () => {
    const { result } = get();
    if (!result) return;
    set({ text: result.corrected_text });
  },
}));
