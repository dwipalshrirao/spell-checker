import SwiftUI

struct ErrorListView: View {
    let errors: [CheckError]
    @Binding var selectedError: CheckError?
    var onApply: ((CheckError) -> Void)?

    var body: some View {
        if errors.isEmpty {
            Text("No errors detected.")
                .font(.caption)
                .foregroundColor(.secondary)
                .italic()
        } else {
            VStack(spacing: 4) {
                ForEach(errors) { error in
                    ErrorRow(error: error, isSelected: selectedError == error, onApply: onApply)
                        .onTapGesture {
                            withAnimation(.easeInOut(duration: 0.15)) {
                                selectedError = selectedError == error ? nil : error
                            }
                        }
                }
            }
        }
    }
}

struct ErrorRow: View {
    let error: CheckError
    let isSelected: Bool
    var onApply: ((CheckError) -> Void)?

    var badgeColor: Color {
        switch error.type {
        case "spelling": return .red
        case "grammar": return .orange
        case "punctuation": return .blue
        case "style": return .purple
        case "word_choice": return .cyan
        default: return .gray
        }
    }

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(error.type.replacingOccurrences(of: "_", with: " ").capitalized)
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundColor(badgeColor)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(badgeColor.opacity(0.15))
                        .cornerRadius(4)

                    Text(error.original)
                        .font(.system(.caption, design: .monospaced))
                        .strikethrough()
                        .foregroundColor(.secondary)

                    Image(systemName: "arrow.right")
                        .font(.caption2)
                        .foregroundColor(.secondary)

                    Text(error.corrected)
                        .font(.system(.caption, design: .monospaced))
                        .fontWeight(.semibold)
                        .foregroundColor(.green)
                }

                if isSelected {
                    Text(error.reason)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.top, 2)
                }
            }
            .padding(8)

            Spacer()

            if let onApply {
                Button("Apply") {
                    onApply(error)
                }
                .buttonStyle(.bordered)
                .tint(.green)
                .controlSize(.small)
                .padding(.trailing, 8)
            }
        }
        .background(backgroundColor)
        .cornerRadius(6)
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(isSelected ? Color.green : Color.clear, lineWidth: 1.5)
        )
    }

    private var backgroundColor: Color {
        switch error.type {
        case "spelling": return Color.red.opacity(0.06)
        case "grammar": return Color.orange.opacity(0.06)
        case "punctuation": return Color.blue.opacity(0.06)
        case "style": return Color.purple.opacity(0.06)
        case "word_choice": return Color.cyan.opacity(0.06)
        default: return Color.gray.opacity(0.06)
        }
    }
}
