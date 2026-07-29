import SwiftUI

struct StatusView: View {
    @Bindable var viewModel: GrammarViewModel

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(viewModel.isBackendHealthy ? Color.green : Color.red)
                .frame(width: 8, height: 8)
            Text("Model: \(viewModel.backendModel)")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}
