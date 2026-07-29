import type { CheckError } from "../types/api";

interface Props {
  errors: CheckError[];
  selectedId: number | null;
  onSelect: (idx: number) => void;
  onApply: (idx: number) => void;
}

const TYPE_COLORS: Record<string, string> = {
  spelling: "bg-red-100 text-red-700 border-red-200",
  grammar: "bg-amber-100 text-amber-700 border-amber-200",
  punctuation: "bg-blue-100 text-blue-700 border-blue-200",
  style: "bg-violet-100 text-violet-700 border-violet-200",
  word_choice: "bg-cyan-100 text-cyan-700 border-cyan-200",
};

export default function ErrorList({ errors, selectedId, onSelect, onApply }: Props) {
  if (errors.length === 0) {
    return <p className="text-sm text-gray-400 italic">No errors detected.</p>;
  }

  return (
    <ul className="space-y-2">
      {errors.map((err, idx) => (
        <li key={idx}>
          <div
            className={`rounded-lg border p-3 text-sm transition-colors cursor-pointer
              ${TYPE_COLORS[err.type] || "bg-gray-100 text-gray-700 border-gray-200"}
              ${selectedId === idx ? "ring-2 ring-emerald-400" : ""}`}
            onClick={() => onSelect(selectedId === idx ? -1 : idx)}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs font-semibold uppercase tracking-wide shrink-0">
                  {err.type}
                </span>
                <span className="text-gray-400 shrink-0">·</span>
                <span className="font-mono text-xs line-through text-gray-500 truncate">
                  {err.original}
                </span>
                <span className="text-gray-400 shrink-0">→</span>
                <span className="font-mono text-xs font-semibold text-emerald-600 truncate">
                  {err.corrected}
                </span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onApply(idx); }}
                className="shrink-0 rounded px-2 py-0.5 text-xs font-medium text-emerald-700 bg-emerald-100 hover:bg-emerald-200 transition-colors"
                title="Apply this fix"
              >
                Apply
              </button>
            </div>
            {selectedId === idx && (
              <p className="mt-1 text-xs text-gray-500">{err.reason}</p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
