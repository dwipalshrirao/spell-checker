import Foundation
import SwiftUI

@MainActor
@Observable
final class GrammarViewModel {
    var text: String = ""
    var result: CheckResponse?
    var isLoading = false
    var errorMessage: String?
    var selectedError: CheckError?
    var isBackendHealthy = false
    var backendModel = "gemma4"
    var isPopoverVisible = false

    private let grammarService = GrammarService()
    private let healthService = HealthService()
    private let feedbackService = FeedbackService()
    private var currentTask: Task<Void, Never>?

    func startCheck() {
        currentTask?.cancel()
        currentTask = Task { @MainActor in
            await checkGrammar()
        }
    }

    private func checkGrammar() async {
        isLoading = true
        errorMessage = nil
        result = nil

        do {
            let response = try await grammarService.check(text: text)
            guard !Task.isCancelled else { isLoading = false; return }
            result = response
        } catch {
            guard !Task.isCancelled else { isLoading = false; return }
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func cancelCheck() {
        currentTask?.cancel()
        currentTask = nil
        isLoading = false
    }

    func checkHealth() async {
        do {
            let health = try await healthService.check()
            isBackendHealthy = health.status == "ok"
            backendModel = health.model
        } catch {
            isBackendHealthy = false
        }
    }

    func sendFeedback(requestId: Int, rating: Int) async {
        do {
            try await feedbackService.send(requestId: requestId, rating: rating)
        } catch {
        }
    }

    func insertCorrectedText() {
        guard let corrected = result?.correctedText else { return }
        text = corrected
    }

    func applyFix(error: CheckError) {
        guard var res = result else { return }
        if let range = text.range(of: error.original) {
            text.replaceSubrange(range, with: error.corrected)
        }
        res.errors.removeAll { $0 == error }
        result = res
        if selectedError == error {
            selectedError = nil
        }
    }
}
