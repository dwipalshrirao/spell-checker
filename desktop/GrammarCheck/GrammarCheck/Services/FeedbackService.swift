import Foundation

actor FeedbackService {
    private let baseURL: String
    private let session: URLSession

    init(baseURL: String = "http://localhost:8000", timeout: TimeInterval = 10) {
        self.baseURL = baseURL
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = timeout
        config.timeoutIntervalForResource = timeout + 5
        self.session = URLSession(configuration: config)
    }

    func send(requestId: Int, rating: Int, comment: String? = nil) async throws {
        guard let url = URL(string: "\(baseURL)/feedback") else {
            throw GrammarServiceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload = FeedbackPayload(requestId: requestId, rating: rating, comment: comment)
        request.httpBody = try JSONEncoder().encode(payload)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? "no body"
            throw GrammarServiceError.serverError(
                (response as? HTTPURLResponse)?.statusCode ?? 0, body
            )
        }
    }
}
