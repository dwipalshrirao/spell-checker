import { useAppStore } from "../store/appStore";
import { computeDiff } from "../utils/diff";
import ErrorList from "./ErrorList";
import DiffView from "./DiffView";

export default function ResultPanel() {
  const result = useAppStore((s) => s.result);
  const text = useAppStore((s) => s.text);
  const selectedError = useAppStore((s) => s.selectedError);
  const setSelectedError = useAppStore((s) => s.setSelectedError);
  const applyFix = useAppStore((s) => s.applyFix);
  const applyAllFixes = useAppStore((s) => s.applyAllFixes);

  if (!result) return null;

  const tokens = computeDiff(text, result.corrected_text);
  const errorCount = result.errors.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Results</h2>
        <span className="text-xs text-gray-400">
          {result.latency_ms != null && `${result.latency_ms.toFixed(0)}ms`}
          {result.latency_ms != null && result.model && " · "}
          {result.model}
        </span>
      </div>

      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Corrected Text
        </h3>
        <DiffView tokens={tokens} />
      </div>

      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Issues ({errorCount})
        </h3>
        <ErrorList
          errors={result.errors}
          selectedId={selectedError ? result.errors.indexOf(selectedError) : null}
          onSelect={(idx) => setSelectedError(result.errors[idx])}
          onApply={applyFix}
        />
      </div>

      {result.summary && (
        <p className="text-xs italic text-gray-400">{result.summary}</p>
      )}

      <div className="flex gap-2">
        <button
          onClick={applyAllFixes}
          disabled={text === result.corrected_text}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          Apply All
        </button>
        <button
          onClick={() => navigator.clipboard.writeText(result.corrected_text)}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
        >
          Copy
        </button>
      </div>
    </div>
  );
}
