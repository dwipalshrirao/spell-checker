import SwiftUI

struct FeedbackView: View {
    let requestId: Int
    @Bindable var viewModel: GrammarViewModel
    @State private var sent = false

    var body: some View {
        if sent {
            Text("Thanks for your feedback!")
                .font(.caption)
                .foregroundColor(.secondary)
        } else {
            HStack(spacing: 8) {
                Text("Was this helpful?")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Button {
                    sent = true
                    Task {
                        try? await viewModel.sendFeedback(requestId: requestId, rating: 5)
                    }
                } label: {
                    Image(systemName: "hand.thumbsup")
                }
                .buttonStyle(.plain)
                .help("Good correction")

                Button {
                    sent = true
                    Task {
                        try? await viewModel.sendFeedback(requestId: requestId, rating: 1)
                    }
                } label: {
                    Image(systemName: "hand.thumbsdown")
                }
                .buttonStyle(.plain)
                .help("Bad correction")
            }
        }
    }
}
