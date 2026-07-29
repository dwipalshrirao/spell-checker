export interface CheckError {
  original: string;
  corrected: string;
  type: string;
  reason: string;
}

export interface CheckResponse {
  corrected_text: string;
  errors: CheckError[];
  summary: string;
  model: string;
  latency_ms: number | null;
  request_id?: number;
}

export interface HealthResponse {
  status: string;
  model: string;
  ollama_reachable: boolean;
  uptime_seconds: number | null;
}

export interface FeedbackPayload {
  request_id: number;
  rating: number;
  comment?: string;
}
