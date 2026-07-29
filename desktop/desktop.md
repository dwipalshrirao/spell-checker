# Desktop — macOS Swift App

Native macOS menu-bar app (LSUIElement, no dock icon) built with SwiftUI + Swift 5.9, targeting macOS 14.0+.

## Directory Layout

```
desktop/GrammarCheck/
  project.yml               # XcodeGen spec (generates .xcodeproj)
  GrammarCheck.xcodeproj/   # Generated — not committed
  GrammarCheck/
    GrammarCheckApp.swift   # @main entry point
    AppDelegate.swift       # Menu bar setup, popover, event handling
    Info.plist
    Models/
      CheckResponse.swift   # Codable structs (CheckResponse, CheckError, …)
    Services/
      GrammarService.swift  # Async HTTP call to Ollama via URLSession
      HealthService.swift   # GET /health
      FeedbackService.swift # POST /feedback with 10s timeout
    ViewModels/
      GrammarViewModel.swift# @Observable state (text, result, applyFix, …)
    Views/
      TextInputView.swift   # Text editor + Cancel / Check Grammar button
      ResultView.swift      # Diff, error list, Apply All / Copy
      ErrorListView.swift   # Per-error rows with individual Apply buttons
      DiffView.swift        # Inline diff display
      FeedbackView.swift    # Thumbs up/down
      StatusView.swift      # Health indicator
      SettingsView.swift    # Model selection, API URL
      PopoverContentView.swift # Root container view
    Utils/
      DiffEngine.swift      # Word-level diff algorithm
```

## How Features Work

### Check Grammar + Cancel

1. User clicks "Check Grammar" → `viewModel.startCheck()` creates a `Task { await checkGrammar() }`, stores it in `currentTask`
2. TextInputView shows loading state, button changes to red **Cancel**
3. `checkGrammar` calls `grammarService.check(text: text)` via async `URLSession.data(for:)`
4. On success → `viewModel.result = response`, text stays in editor
5. On error → `viewModel.errorMessage` set, displayed in the popover
6. **Cancel**: Clicking Cancel calls `viewModel.cancelCheck()` → `currentTask?.cancel()` + `currentTask = nil` + `isLoading = false`. The in-flight `URLSession` request continues server-side but its result is discarded because `Task.isCancelled` is checked right after the network call returns.

### Individual Apply ("Apply" per error)

1. Each `ErrorRow` in `ErrorListView` has a green **Apply** button
2. Clicking calls `viewModel.applyFix(error:)` → finds `error.original` in `viewModel.text` via `String.range(of:)`, replaces with `error.corrected`
3. Removes the matched error from `result.errors`, clears `selectedError` if it was the applied one
4. Error disappears from list; diff view re-renders

### Apply All

1. Calls `viewModel.insertCorrectedText()` → sets `viewModel.text = result.correctedText`
2. Button is **disabled** when `viewModel.text == result.correctedText`
3. If user edits the textbox manually, button re-enables

### Copy

- `NSPasteboard.general.clearContents()` + `NSPasteboard.general.setString(result.correctedText, forType: .string)`
- Copies the API's full corrected text

### Diff View

- `computeDiff(original:viewModel.text, corrected:result.correctedText)` using the same word-level Levenshtein algorithm as frontend
- Returns tokens rendered with green/red/plain styling in SwiftUI

### Health Status

- `viewModel.checkHealth()` called once in `.task {}` on popover appear
- Makes `GET /health` via `HealthService`, sets `isBackendHealthy` + `backendModel`
- `StatusView` reads these bindings → green dot + model name, or red dot + "Not connected"

### Feedback

1. User clicks thumbs up/down → `FeedbackView` immediately hides buttons, shows "Thanks!"
2. In background, `FeedbackService.send(requestId:rating:)` fires with its own `URLSession` configured with 10s timeout
3. Errors are silently caught

### Global Hotkey (Ctrl+Shift+G)

- `AppDelegate` registers a global `NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged)` monitor
- When modifier keys match `Cmd + Shift + G`, toggles the popover visibility
- No accessibility permissions required

```bash
# Generate .xcodeproj from spec (one-time after clone)
xcodegen generate

# Open in Xcode
open GrammarCheck.xcodeproj

# Build (CLI)
xcodebuild -project GrammarCheck.xcodeproj -scheme GrammarCheck build
```

## Key Details

- **16 Swift source files** across 6 directories
- **Min deployment target**: macOS 14.0
- **Build**: Succeeds clean, zero warnings
- **No external dependencies** — uses Foundation, SwiftUI, Combine only
