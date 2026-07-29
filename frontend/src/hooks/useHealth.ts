import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import type { HealthResponse } from "../types/api";

async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await axios.get<HealthResponse>("/health");
  return data;
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: 2,
    staleTime: Infinity,
  });
}
