import SwiftUI

struct ResultView: View {
    @Bindable var viewModel: GrammarViewModel

    var body: some View {
        guard let result = viewModel.result else {
            return AnyView(EmptyView())
        }

        let tokens = computeDiff(original: viewModel.text, corrected: result.correctedText)

        return AnyView(
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("Results")
                        .font(.headline)
                    Spacer()
                    if let latency = result.latencyMs {
                        Text("\(Int(latency))ms · \(result.model)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Corrected Text")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)

                    DiffView(tokens: tokens)
                        .padding(8)
                        .background(Color(.textBackgroundColor))
                        .cornerRadius(6)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Issues (\(result.errors.count))")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)

                    ErrorListView(errors: result.errors, selectedError: $viewModel.selectedError, onApply: { viewModel.applyFix(error: $0) })
                }

                if !result.summary.isEmpty {
                    Text(result.summary)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .italic()
                }

                HStack {
                    Spacer()
                    Button("Copy") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(result.correctedText, forType: .string)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    Button("Apply All") {
                        viewModel.insertCorrectedText()
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)
                    .disabled(viewModel.text == result.correctedText)
                }
            }
        )
    }
}
