# Frontend — React + TypeScript Web App

Vite-based SPA with TanStack Query, Zustand, Tailwind CSS, and Axios.

## Directory Layout

```
frontend/
  src/
    App.tsx               # Root component
    main.tsx              # Entry point
    index.css             # Tailwind base styles
    components/
      TextEditor.tsx      # Text input + Cancel/Check button
      ResultPanel.tsx     # Diff view, error list, Apply All / Copy
      ErrorList.tsx       # Per-error rows with individual Apply buttons
      DiffView.tsx        # Inline diff display (same/removed/added tokens)
      FeedbackBar.tsx     # Thumbs up/down with immediate UI + 10s timeout
      StatusBar.tsx       # Live health indicator (green/red dot + model name)
    hooks/
      useGrammarCheck.ts  # Mutation + AbortController + cancel()
      useHealth.ts        # Single health query (no polling)
    store/
      appStore.ts         # Zustand store (text, result, errors, applyFix/applyAll)
    types/
      api.ts              # TypeScript interfaces for API payloads
    utils/
      diff.ts             # Levenshtein-based word diff engine
      applyFixes.ts       # findFirstMatch + applySingleFix helpers
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server (port 5173) |
| `npm run build` | `tsc && vite build` |
| `npm run preview` | Preview production build |

## Dependencies

- **react** 18, **react-dom** 18, **@tanstack/react-query** 5, **zustand** 4, **axios** 1

## How Features Work

### Check Grammar + Cancel

1. User clicks "Check Grammar" → `useGrammarCheck` creates an `AbortController` + calls `axios.post("/check", { text }, { signal })`
2. TextEditor shows loading spinner, button changes to red **Cancel**
3. On success → Zustand store updated with `result` (errors, corrected_text, model, latency)
4. On error → error message displayed, submit state reset
5. **Cancel**: Clicking Cancel calls `controller.abort()` → Axios throws `isCancel` error → `useGrammarCheck` catches it, ignores it, resets state to idle. Abort also cancels the in-flight backend request.
6. `useMutation` hooks: `onMutate` sets loading, `onSuccess` sets result, `onError` catches all errors except cancellation

### Individual Apply ("Apply" per error)

1. Each `ErrorRow` in `ErrorList` has a green **Apply** button
2. Clicking calls `store.applyFix(index)` → reads `result.errors[index]`, calls `applySingleFix(text, original, corrected)`
3. `applySingleFix` uses `text.indexOf(original)` to find the first occurrence, then replaces via `text.slice(0, start) + corrected + text.slice(end)`
4. Store updates `text` + removes the applied error from `result.errors`
5. Error disappears from list; diff view re-renders showing remaining differences

### Apply All

1. Calls `store.applyAllFixes()` → sets `text = result.corrected_text` directly (trusts the LLM's full output)
2. Button is **disabled** when `text === result.corrected_text` (already applied or user reverted)
3. If user manually edits the textbox, the button re-enables

### Copy

- `navigator.clipboard.writeText(result.corrected_text)` — standard async clipboard API
- Copies the API's full corrected text, regardless of partial individual applies

### Diff View

- `computeDiff(original, corrected)` in `utils/diff.ts` is a word-level Levenshtein distance algorithm
- Tokenizes both strings by whitespace, computes edit distance matrix, walks back to produce `DiffToken[]` with types: `same`, `removed`, `added`
- `DiffView` renders each token: green background for added, red strikethrough for removed, plain for same

### Live Health Status

- `useHealth` fires a single `GET /health` on page mount via TanStack Query
- `staleTime: Infinity` and no `refetchInterval` — one call, never polls
- StatusBar receives `health` prop → green dot + "Model: {name}" if healthy, red dot + "Not connected" if not

### Feedback

1. User clicks thumbs up/down → `sent = true` immediately (instant "Thanks for your feedback!")
2. In parallel, `axios.post("/feedback", { request_id, rating })` fires with 10s timeout via AbortController
3. Errors are silently ignored — feedback is best-effort

### Keyboard Shortcut

- `TextEditor` captures `onKeyDown` → if `Cmd/Ctrl + Enter` pressed, calls `onSubmit()`
- Same flow as clicking the Check button

```bash
npm install
npm run build   # → dist/ (13.26 kB CSS, 243.33 kB JS gzipped)
```

## Dev Proxy

Vite proxies `/check`, `/health`, `/ready`, `/feedback`, `/metrics` to `http://localhost:8000`.
