export interface MatchResult {
  start: number;
  end: number;
}

export function findFirstMatch(text: string, original: string): MatchResult | null {
  const start = text.indexOf(original);
  if (start === -1) return null;
  return { start, end: start + original.length };
}

export function applySingleFix(text: string, original: string, corrected: string): { newText: string; found: boolean } {
  const match = findFirstMatch(text, original);
  if (!match) return { newText: text, found: false };
  return {
    newText: text.slice(0, match.start) + corrected + text.slice(match.end),
    found: true,
  };
}
