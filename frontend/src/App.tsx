import { useGrammarCheck } from "./hooks/useGrammarCheck";
import { useHealth } from "./hooks/useHealth";
import { useAppStore } from "./store/appStore";
import TextEditor from "./components/TextEditor";
import ResultPanel from "./components/ResultPanel";
import FeedbackBar from "./components/FeedbackBar";
import StatusBar from "./components/StatusBar";

export default function App() {
  const text = useAppStore((s) => s.text);
  const submitState = useAppStore((s) => s.submitState);
  const result = useAppStore((s) => s.result);
  const errorMessage = useAppStore((s) => s.errorMessage);

  const { mutate, cancel } = useGrammarCheck();
  const { data: health } = useHealth();

  const handleCheck = () => {
    mutate(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      handleCheck();
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">GrammarCheck</h1>
        <StatusBar health={health} />
      </header>

      <main className="flex-1 space-y-6">
        <TextEditor onSubmit={handleCheck} onCancel={cancel} onKeyDown={handleKeyDown} />

        {submitState === "loading" && (
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-600" />
            <span className="ml-3 text-sm text-gray-500">Checking grammar…</span>
          </div>
        )}

        {errorMessage && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {errorMessage}
          </div>
        )}

        {result && <ResultPanel />}

        {result && (
          <FeedbackBar requestId={result.request_id ?? 0} />
        )}
      </main>

      <footer className="mt-8 border-t border-gray-100 pt-4 text-center text-xs text-gray-400">
        Powered by local Ollama · All text stays on your machine
      </footer>
    </div>
  );
}
