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

export interface VocabCard {
  id: number;
  term: string;
  translation: string;
  example_sentence: string;
  due_date: string;
}

export async function getDueCards(): Promise<VocabCard[]> {
  const response = await fetch(`${API_BASE_URL}/api/vocab/due`);
  if (!response.ok) {
    throw new Error(`Failed to fetch due cards: ${response.status}`);
  }
  return response.json();
}

export async function answerVocabCard(cardId: number, answer: string): Promise<{ correct: boolean }> {
  const response = await fetch(`${API_BASE_URL}/api/vocab/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id: cardId, answer }),
  });
  if (!response.ok) {
    throw new Error(`Failed to submit answer: ${response.status}`);
  }
  return response.json();
}

export interface LearningPlanResponse {
  topics: string[];
}

export async function getLearningPlan(): Promise<LearningPlanResponse | null> {
  const response = await fetch(`${API_BASE_URL}/api/learning-plan`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to fetch learning plan: ${response.status}`);
  }
  return response.json();
}
