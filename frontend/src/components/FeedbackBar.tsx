import { useState, useRef } from "react";
import axios from "axios";

interface Props {
  requestId: number;
}

const TIMEOUT_MS = 10_000;

export default function FeedbackBar({ requestId }: Props) {
  const [sent, setSent] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const send = async (rating: number) => {
    setSent(true);
    const controller = new AbortController();
    timerRef.current = setTimeout(() => controller.abort(), TIMEOUT_MS);
    try {
      await axios.post("/feedback", { request_id: requestId, rating }, { signal: controller.signal });
    } catch {
      // silently fail
    } finally {
      clearTimeout(timerRef.current);
    }
  };

  if (sent) {
    return <p className="text-xs text-gray-400">Thanks for your feedback!</p>;
  }

  return (
    <div className="flex items-center gap-3 text-sm text-gray-500">
      <span className="text-xs">Was this helpful?</span>
      <button onClick={() => send(5)} className="hover:text-emerald-600 transition-colors">
        👍
      </button>
      <button onClick={() => send(1)} className="hover:text-red-500 transition-colors">
        👎
      </button>
    </div>
  );
}
