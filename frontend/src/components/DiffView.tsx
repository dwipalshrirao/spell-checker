import type { DiffToken } from "../utils/diff";

interface Props {
  tokens: DiffToken[];
}

export default function DiffView({ tokens }: Props) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm leading-relaxed">
      {tokens.map((t, i) => {
        if (t.type === "same") {
          return <span key={i}>{t.text}</span>;
        }
        if (t.type === "removed") {
          return (
            <span key={i} className="inline bg-red-100 text-red-700 line-through decoration-red-500 rounded px-0.5">
              {t.text}
            </span>
          );
        }
        return (
          <span key={i} className="inline bg-emerald-100 text-emerald-700 rounded px-0.5">
            {t.text}
          </span>
        );
      })}
    </div>
  );
}
