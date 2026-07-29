import SwiftUI

struct PopoverContentView: View {
    @Bindable var viewModel: GrammarViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("GrammarCheck")
                    .font(.headline)
                Spacer()
                StatusView(viewModel: viewModel)
            }

            TextInputView(viewModel: viewModel) {
                viewModel.startCheck()
            }

            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    if viewModel.isLoading {
                        HStack {
                            ProgressView()
                                .scaleEffect(0.8)
                            Text("Checking grammar...")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Spacer()
                            Button("Cancel") {
                                viewModel.cancelCheck()
                            }
                            .buttonStyle(.link)
                            .controlSize(.small)
                        }
                        .padding(.vertical, 4)
                    }

                    if let error = viewModel.errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                            .padding(8)
                            .background(Color.red.opacity(0.1))
                            .cornerRadius(6)
                    }

                    if let result = viewModel.result {
                        ResultView(viewModel: viewModel)
                        FeedbackView(requestId: result.requestId ?? 0, viewModel: viewModel)
                    }
                }
            }
        }
        .padding()
        .frame(width: 380)
    }
}
