export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ProfileResponse {
  language: string;
  cefr_level: string;
}

export async function getProfile(): Promise<ProfileResponse> {
  const response = await fetch(`${API_BASE_URL}/api/profile`);
  if (!response.ok) {
    throw new Error(`Failed to fetch profile: ${response.status}`);
  }
  return response.json();
}

export interface PracticeTurnResponse {
  reply: string;
}

export async function sendPracticeTurn(message: string): Promise<PracticeTurnResponse> {
  const response = await fetch(`${API_BASE_URL}/api/dialog/practice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error(`Failed to send turn: ${response.status}`);
  }
  return response.json();
}

export interface PlacementStartResponse {
  session_id: number;
  question: string;
}

export async function startPlacement(): Promise<PlacementStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/dialog/placement/start`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to start placement: ${response.status}`);
  }
  return response.json();
}

export interface PlacementAnswerResponse {
  finished: boolean;
  question?: string;
  level?: string;
}

export async function answerPlacement(
  sessionId: number,
  answer: string,
): Promise<PlacementAnswerResponse> {
  const response = await fetch(`${API_BASE_URL}/api/dialog/placement/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, answer }),
  });
  if (!response.ok) {
    throw new Error(`Failed to answer placement: ${response.status}`);
  }
  return response.json();
}
