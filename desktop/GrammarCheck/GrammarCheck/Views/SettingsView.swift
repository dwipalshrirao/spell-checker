import SwiftUI

struct SettingsView: View {
    @Bindable var viewModel: GrammarViewModel
    @State private var backendURL = "http://localhost:8000"
    @State private var launchAtLogin = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Settings")
                .font(.title2)
                .fontWeight(.semibold)

            GroupBox("Backend") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("URL:")
                            .font(.caption)
                        TextField("http://localhost:8000", text: $backendURL)
                            .textFieldStyle(.roundedBorder)
                    }

                    HStack {
                        Text("Status:")
                            .font(.caption)
                        Circle()
                            .fill(viewModel.isBackendHealthy ? Color.green : Color.red)
                            .frame(width: 8, height: 8)
                        Text(viewModel.isBackendHealthy ? "Connected" : "Disconnected")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Button("Check Connection") {
                        Task { await viewModel.checkHealth() }
                    }
                    .buttonStyle(.borderless)
                }
            }
            .padding()
            .frame(width: 320, height: 200)
        }
    }
}