import type { HealthResponse } from "../types/api";

interface Props {
  health?: HealthResponse;
}

export default function StatusBar({ health }: Props) {
  const healthy = health?.status !== undefined;
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          healthy ? "bg-emerald-400" : "bg-red-400"
        }`}
      />
      <span>{healthy ? `Model: ${health.model}` : "Not connected"}</span>
    </div>
  );
}
