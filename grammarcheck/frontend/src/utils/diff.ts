export interface DiffToken {
  text: string;
  type: "same" | "removed" | "added";
}

export function computeDiff(original: string, corrected: string): DiffToken[] {
  const origWords = tokenize(original);
  const corrWords = tokenize(corrected);
  return levenshteinDiff(origWords, corrWords);
}

function tokenize(text: string): string[] {
  return text.match(/\S+\s*/g) || [];
}

function levenshteinDiff(orig: string[], corr: string[]): DiffToken[] {
  const m = orig.length;
  const n = corr.length;
  const dp: { cost: number; op: "keep" | "delete" | "insert" | "replace" }[][] = [];

  for (let i = 0; i <= m; i++) {
    dp[i] = [];
    for (let j = 0; j <= n; j++) {
      if (i === 0 && j === 0) dp[i][j] = { cost: 0, op: "keep" };
      else if (i === 0) dp[i][j] = { cost: j, op: "insert" };
      else if (j === 0) dp[i][j] = { cost: i, op: "delete" };
      else {
        const cost = orig[i - 1] === corr[j - 1] ? 0 : 1;
        const del = dp[i - 1][j].cost + 1;
        const ins = dp[i][j - 1].cost + 1;
        const sub = dp[i - 1][j - 1].cost + cost;
        const min = Math.min(del, ins, sub);
        if (min === sub) dp[i][j] = { cost: sub, op: cost === 0 ? "keep" : "replace" };
        else if (min === del) dp[i][j] = { cost: del, op: "delete" };
        else dp[i][j] = { cost: ins, op: "insert" };
      }
    }
  }

  const result: DiffToken[] = [];
  let i = m, j = n;
  while (i > 0 || j > 0) {
    const op = dp[i][j].op;
    if (op === "keep") {
      result.unshift({ text: orig[i - 1], type: "same" });
      i--; j--;
    } else if (op === "delete") {
      result.unshift({ text: orig[i - 1], type: "removed" });
      i--;
    } else if (op === "insert") {
      result.unshift({ text: corr[j - 1], type: "added" });
      j--;
    } else {
      result.unshift({ text: orig[i - 1], type: "removed" });
      result.unshift({ text: corr[j - 1], type: "added" });
      i--; j--;
    }
  }
  return result;
}
