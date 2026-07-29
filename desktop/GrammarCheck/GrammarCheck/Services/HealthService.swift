import Foundation

actor HealthService {
    private let baseURL: String
    private let session: URLSession

    init(baseURL: String = "http://localhost:8000") {
        self.baseURL = baseURL
        self.session = URLSession.shared
    }

    func check() async throws -> HealthResponse {
        guard let url = URL(string: "\(baseURL)/health") else {
            throw GrammarServiceError.invalidURL
        }

        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw GrammarServiceError.backendUnreachable
        }

        return try JSONDecoder().decode(HealthResponse.self, from: data)
    }
}
