import SwiftUI

struct DiffView: View {
    let tokens: [DiffToken]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(tokens) { token in
                switch token.type {
                case .same:
                    Text(token.text)
                        .foregroundColor(.primary)
                case .removed:
                    Text(token.text)
                        .foregroundColor(.red)
                        .strikethrough(true, color: .red)
                        .background(Color.red.opacity(0.1))
                case .added:
                    Text(token.text)
                        .foregroundColor(.green)
                        .background(Color.green.opacity(0.1))
                }
            }
        }
        .lineSpacing(4)
    }
}
