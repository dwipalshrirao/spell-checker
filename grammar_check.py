#!/usr/bin/env python3
"""
GrammarCheck — Phase 1
Uses a locally running Ollama model (default: gemma4:e4b) to:
  1. Correct spelling & grammar mistakes
  2. Explain every change with a reason
  3. Show a clean diff between original and corrected text

Usage:
  python grammar_check.py                        # interactive mode (type/paste text)
  python grammar_check.py "your text here"       # inline text argument
  cat myfile.txt | python grammar_check.py       # pipe from file or stdin
  python grammar_check.py --model gemma3:4b      # use a different local model
"""

import sys
import json
import argparse
import textwrap
import requests
import difflib

# ─── CONFIG ───────────────────────────────────────────────────────────────────

OLLAMA_URL   = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma4"
# DEFAULT_MODEL = "gemma4:e4b"

SYSTEM_PROMPT = """\
You are an expert English grammar and spelling checker.
Your job is to analyse text submitted by the user, find ALL errors, and return a JSON response.

Return ONLY valid JSON — no markdown, no code fences, no extra text.

The JSON must follow this exact schema:
{
  "corrected_text": "<full corrected version of the text>",
  "errors": [
    {
      "original": "<exact wrong word/phrase from input>",
      "corrected": "<correct word/phrase>",
      "type": "<one of: spelling | grammar | punctuation | style | word_choice>",
      "reason": "<clear, concise explanation of why this is wrong and what the fix does>"
    }
  ],
  "summary": "<one-sentence overall assessment of the text quality>"
}

Rules:
- If the text has no errors, return an empty list for "errors" and say so in summary.
- Preserve the original meaning — do not rewrite sentences unnecessarily.
- Be specific in reasons, e.g. "misteks → mistakes: phonetic misspelling" not just "wrong spelling".
- Identify overlapping errors as separate items when the error type differs.
"""

# ─── COLOURS (terminal) ───────────────────────────────────────────────────────

class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def bold(s):   return f"{C.BOLD}{s}{C.RESET}"
def red(s):    return f"{C.RED}{s}{C.RESET}"
def green(s):  return f"{C.GREEN}{s}{C.RESET}"
def yellow(s): return f"{C.YELLOW}{s}{C.RESET}"
def cyan(s):   return f"{C.CYAN}{s}{C.RESET}"
def dim(s):    return f"{C.DIM}{s}{C.RESET}"

ERROR_TYPE_COLOURS = {
    "spelling":    C.RED,
    "grammar":     C.YELLOW,
    "punctuation": C.CYAN,
    "style":       C.GREEN,
    "word_choice": "\033[95m",   # magenta
}

def colour_type(error_type: str) -> str:
    col = ERROR_TYPE_COLOURS.get(error_type.lower(), C.RESET)
    return f"{col}{error_type.upper()}{C.RESET}"

# ─── OLLAMA CALL ──────────────────────────────────────────────────────────────

def check_ollama_running():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def call_ollama(text: str, model: str) -> dict:
    """Send text to Ollama and return parsed JSON result."""
    payload = {
        "model":  model,
        "system": SYSTEM_PROMPT,
        "prompt": text,
        "stream": False,
        "format": "json",       # Ollama native JSON mode — forces valid JSON output
        "options": {
            "temperature": 0.1, # low temp = more deterministic corrections
            "top_p": 0.9,
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(red("\n✗ Cannot connect to Ollama."))
        print(dim("  Make sure Ollama is running:  ollama serve"))
        print(dim(f"  And the model is pulled:      ollama pull {model}"))
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(red("\n✗ Ollama timed out. The model may still be loading — try again."))
        sys.exit(1)

    raw = response.json().get("response", "")

    # Strip markdown fences if model ignores format=json
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(red("\n✗ Model returned non-JSON output. Raw response:"))
        print(dim(raw[:500]))
        sys.exit(1)

# ─── INLINE DIFF ─────────────────────────────────────────────────────────────

def word_diff(original: str, corrected: str) -> str:
    """Show a word-level diff: red = removed, green = added."""
    orig_words = original.split()
    corr_words = corrected.split()

    matcher = difflib.SequenceMatcher(None, orig_words, corr_words)
    parts = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            parts.append(" ".join(orig_words[i1:i2]))
        elif tag == "replace":
            parts.append(red("~~" + " ".join(orig_words[i1:i2]) + "~~"))
            parts.append(green(" ".join(corr_words[j1:j2])))
        elif tag == "delete":
            parts.append(red("~~" + " ".join(orig_words[i1:i2]) + "~~"))
        elif tag == "insert":
            parts.append(green(" ".join(corr_words[j1:j2])))

    return " ".join(parts)

# ─── DISPLAY ─────────────────────────────────────────────────────────────────

def display_results(original: str, result: dict):
    errors   = result.get("errors", [])
    corrected = result.get("corrected_text", original)
    summary  = result.get("summary", "")

    width = min(80, 100)
    sep   = dim("─" * width)

    print(f"\n{bold('─── GRAMMAR CHECK RESULTS ───────────────────────────────────────')}")

    # ── Summary
    print(f"\n{bold('Summary')}")
    print(f"  {summary}")

    # ── Error count badge
    n = len(errors)
    if n == 0:
        badge = green("✓ No errors found")
    elif n <= 3:
        badge = yellow(f"⚠  {n} issue{'s' if n > 1 else ''} found")
    else:
        badge = red(f"✗  {n} issues found")

    print(f"\n{bold('Issues')}  {badge}")

    if errors:
        print()
        for i, err in enumerate(errors, 1):
            etype    = err.get("type", "unknown")
            original_frag = err.get("original", "")
            fixed_frag    = err.get("corrected", "")
            reason   = err.get("reason", "")

            print(f"  {dim(str(i) + '.')}")
            print(f"  {colour_type(etype)}")
            print(f"  {red(repr(original_frag))}  →  {green(repr(fixed_frag))}")
            # Wrap reason
            wrapped = textwrap.fill(reason, width=width - 4,
                                    initial_indent="  ", subsequent_indent="  ")
            print(dim(wrapped))
            print()

    # ── Corrected text
    print(sep)
    print(bold("Corrected Text"))
    print()
    print(textwrap.fill(corrected, width=width, initial_indent="  ",
                        subsequent_indent="  "))

    # ── Word diff
    if errors:
        print()
        print(sep)
        print(bold("Diff")  + dim("  (~~red~~ = removed   green = added)"))
        print()
        print(textwrap.fill(word_diff(original, corrected), width=width,
                            initial_indent="  ", subsequent_indent="  "))

    print(f"\n{sep}\n")

# ─── GET INPUT TEXT ──────────────────────────────────────────────────────────

def get_input_text(args) -> str:
    # 1. Inline argument
    if args.text:
        return " ".join(args.text)

    # 2. Piped stdin (non-interactive)
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    # 3. Interactive prompt
    print(bold("\n── GrammarCheck (Phase 1) ──────────────────────────────────────"))
    print(dim(f"  Model: {args.model}  |  Ollama: {OLLAMA_URL}"))
    print(dim("  Paste or type your text below, then press Enter twice (blank line) to submit."))
    print(dim("  Type 'quit' to exit.\n"))

    lines = []
    try:
        while True:
            line = input()
            if line.strip().lower() in ("quit", "exit", "q"):
                print(dim("Bye!"))
                sys.exit(0)
            if line == "" and lines:
                break
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    return "\n".join(lines).strip()

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GrammarCheck — local AI-powered spelling & grammar checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          python grammar_check.py "I has went to teh store yesterday."
          echo "She dont likes coffee" | python grammar_check.py
          python grammar_check.py --model gemma3:4b "He runned very fastly."
          cat essay.txt | python grammar_check.py
        """)
    )
    parser.add_argument("text", nargs="*", help="Text to check (optional; reads stdin or prompts if omitted)")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"Ollama model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON instead of formatted display")

    args = parser.parse_args()

    # Check Ollama is reachable before doing anything else
    if not check_ollama_running():
        print(red("✗ Ollama is not running."))
        print(dim("  Start it with:  ollama serve"))
        print(dim(f"  Then pull:      ollama pull {args.model}"))
        sys.exit(1)

    text = get_input_text(args)
    if not text:
        print(yellow("No text provided. Exiting."))
        sys.exit(0)

    print(dim(f"\n  Checking with {args.model}…  (this may take 5-15 seconds)"), end="", flush=True)

    result = call_ollama(text, args.model)

    print("\r" + " " * 60 + "\r", end="")  # clear the "Checking…" line

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        display_results(text, result)

if __name__ == "__main__":
    main()
