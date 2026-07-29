import Foundation

enum GrammarServiceError: LocalizedError {
    case invalidURL
    case networkError(String)
    case decodingError(String)
    case serverError(Int, String)
    case backendUnreachable

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid backend URL. Make sure the backend is running on localhost:8000."
        case .networkError(let msg):
            return "Network error: \(msg). Is the backend running?"
        case .decodingError(let msg):
            return "Failed to parse response: \(msg)"
        case .serverError(let code, let body):
            return "Server error (\(code)): \(body)"
        case .backendUnreachable:
            return "Cannot reach the backend. Run `make dev` in the backend directory."
        }
    }
}

actor GrammarService {
    private let baseURL: String
    private let session: URLSession
    private let timeout: TimeInterval

    init(baseURL: String = "http://localhost:8000", timeout: TimeInterval = 120) {
        self.baseURL = baseURL
        self.timeout = timeout
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = timeout
        config.timeoutIntervalForResource = timeout + 30
        self.session = URLSession(configuration: config)
    }

    func check(text: String) async throws -> CheckResponse {
        guard let url = URL(string: "\(baseURL)/check") else {
            throw GrammarServiceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(CheckRequest(text: text))

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw GrammarServiceError.networkError(error.localizedDescription)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw GrammarServiceError.backendUnreachable
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? "no body"
            throw GrammarServiceError.serverError(httpResponse.statusCode, body)
        }

        do {
            return try JSONDecoder().decode(CheckResponse.self, from: data)
        } catch {
            throw GrammarServiceError.decodingError(error.localizedDescription)
        }
    }
}
