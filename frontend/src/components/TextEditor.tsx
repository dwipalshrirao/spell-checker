import { useAppStore } from "../store/appStore";

interface Props {
  onSubmit: () => void;
  onCancel: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
}

const MAX_CHARS = 5000;

export default function TextEditor({ onSubmit, onCancel, onKeyDown }: Props) {
  const text = useAppStore((s) => s.text);
  const setText = useAppStore((s) => s.setText);
  const submitState = useAppStore((s) => s.submitState);

  const charCount = text.length;
  const isOver = charCount > MAX_CHARS;

  return (
    <div className="space-y-2">
      <textarea
        className={`w-full rounded-lg border p-4 text-sm focus:outline-none focus:ring-2 resize-y min-h-[140px] ${
          isOver
            ? "border-red-400 focus:ring-red-400"
            : "border-gray-300 focus:ring-emerald-500"
        }`}
        placeholder="Paste or type your text here..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={submitState === "loading"}
      />
      <div className="flex items-center justify-between">
        <span
          className={`text-xs ${isOver ? "text-red-500 font-semibold" : "text-gray-400"}`}
        >
          {charCount}/{MAX_CHARS}
        </span>
        {submitState === "loading" ? (
          <button
            onClick={onCancel}
            className="rounded-lg bg-red-500 px-5 py-2 text-sm font-medium text-white
                       hover:bg-red-600 transition-colors"
          >
            Cancel
          </button>
        ) : (
          <button
            onClick={onSubmit}
            disabled={text.trim().length < 3 || isOver}
            className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white
                       hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40
                       transition-colors"
          >
            Check Grammar
          </button>
        )}
      </div>
    </div>
  );
}
