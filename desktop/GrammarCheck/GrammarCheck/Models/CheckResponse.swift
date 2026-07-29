import Foundation

struct CheckRequest: Codable {
    let text: String
}

struct CheckError: Codable, Identifiable, Hashable {
    let original: String
    let corrected: String
    let type: String
    let reason: String

    var id: String { "\(original)|\(corrected)|\(type)" }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
    static func == (lhs: CheckError, rhs: CheckError) -> Bool {
        lhs.id == rhs.id
    }
}

struct CheckResponse: Codable {
    let correctedText: String
    var errors: [CheckError]
    let summary: String
    let model: String
    let latencyMs: Double?
    let requestId: Int?

    enum CodingKeys: String, CodingKey {
        case correctedText = "corrected_text"
        case errors, summary, model
        case latencyMs = "latency_ms"
        case requestId = "request_id"
    }
}

struct HealthResponse: Codable {
    let status: String
    let model: String
    let ollamaReachable: Bool
    let uptimeSeconds: Double?

    enum CodingKeys: String, CodingKey {
        case status, model
        case ollamaReachable = "ollama_reachable"
        case uptimeSeconds = "uptime_seconds"
    }
}

struct FeedbackPayload: Codable {
    let requestId: Int
    let rating: Int
    let comment: String?

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case rating, comment
    }
}
