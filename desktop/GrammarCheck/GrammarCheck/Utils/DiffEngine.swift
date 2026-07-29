import Foundation

enum DiffType {
    case same, removed, added
}

struct DiffToken: Identifiable {
    let id = UUID()
    let text: String
    let type: DiffType
}

func computeDiff(original: String, corrected: String) -> [DiffToken] {
    let origWords = tokenize(original)
    let corrWords = tokenize(corrected)
    return levenshteinDiff(orig: origWords, corr: corrWords)
}

private func tokenize(_ text: String) -> [String] {
    var tokens: [String] = []
    let pattern = try! NSRegularExpression(pattern: #"\S+\s*"#)
    let matches = pattern.matches(in: text, range: NSRange(text.startIndex..., in: text))
    for match in matches {
        if let range = Range(match.range, in: text) {
            tokens.append(String(text[range]))
        }
    }
    return tokens
}

private func levenshteinDiff(orig: [String], corr: [String]) -> [DiffToken] {
    let m = orig.count
    let n = corr.count

    enum Op { case keep, delete, insert, replace }
    var dp: [(cost: Int, op: Op)] = Array(repeating: (cost: 0, op: .keep), count: (m + 1) * (n + 1))

    func idx(_ i: Int, _ j: Int) -> Int { i * (n + 1) + j }

    for i in 0...m {
        for j in 0...n {
            if i == 0 && j == 0 {
                dp[idx(i, j)] = (0, .keep)
            } else if i == 0 {
                dp[idx(i, j)] = (j, .insert)
            } else if j == 0 {
                dp[idx(i, j)] = (i, .delete)
            } else {
                let cost = orig[i - 1] == corr[j - 1] ? 0 : 1
                let del = dp[idx(i - 1, j)].cost + 1
                let ins = dp[idx(i, j - 1)].cost + 1
                let sub = dp[idx(i - 1, j - 1)].cost + cost
                let minCost = min(del, ins, sub)
                if minCost == sub {
                    dp[idx(i, j)] = (sub, cost == 0 ? .keep : .replace)
                } else if minCost == del {
                    dp[idx(i, j)] = (del, .delete)
                } else {
                    dp[idx(i, j)] = (ins, .insert)
                }
            }
        }
    }

    var result: [DiffToken] = []
    var i = m, j = n
    while i > 0 || j > 0 {
        let op = dp[idx(i, j)].op
        switch op {
        case .keep:
            result.insert(DiffToken(text: orig[i - 1], type: .same), at: 0)
            i -= 1; j -= 1
        case .delete:
            result.insert(DiffToken(text: orig[i - 1], type: .removed), at: 0)
            i -= 1
        case .insert:
            result.insert(DiffToken(text: corr[j - 1], type: .added), at: 0)
            j -= 1
        case .replace:
            result.insert(DiffToken(text: orig[i - 1], type: .removed), at: 0)
            result.insert(DiffToken(text: corr[j - 1], type: .added), at: 0)
            i -= 1; j -= 1
        }
    }
    return result
}
