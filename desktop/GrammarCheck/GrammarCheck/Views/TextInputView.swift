import SwiftUI

struct TextInputView: View {
    @Bindable var viewModel: GrammarViewModel
    let onSubmit: () -> Void

    private let maxChars = 5000

    var body: some View {
        VStack(spacing: 8) {
            TextEditor(text: $viewModel.text)
                .font(.system(size: 13))
                .frame(minHeight: 100, maxHeight: 200)
                .padding(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(viewModel.text.count > maxChars ? Color.red : Color.gray.opacity(0.3), lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: 8))

            HStack {
                Text("\(viewModel.text.count)/\(maxChars)")
                    .font(.caption)
                    .foregroundColor(viewModel.text.count > maxChars ? .red : .secondary)

                Spacer()

                if viewModel.isLoading {
                    Button(role: .destructive) {
                        Task { @MainActor in
                            viewModel.cancelCheck()
                        }
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 14))
                        Text("Cancel")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                } else {
                    Button(action: {
                        Task { @MainActor in
                            viewModel.startCheck()
                        }
                    }) {
                        Text("Check Grammar")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)
                    .disabled(viewModel.text.trimmingCharacters(in: .whitespacesAndNewlines).count < 3
                              || viewModel.text.count > maxChars)
                }
            }
        }
    }
}
