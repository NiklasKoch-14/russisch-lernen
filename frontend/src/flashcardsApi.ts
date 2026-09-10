import { API_BASE_URL } from "./api";
import type { FlashcardResult, FlashcardRound } from "./courseTypes";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Anfrage fehlgeschlagen (${response.status}): ${path}`);
  }
  return response.json() as Promise<T>;
}

/** `direction` ist "ru_de", "de_ru" oder "mixed". */
export const getFlashcardRound = (direction: string) =>
  request<FlashcardRound>(`/flashcards/round?direction=${direction}`);

export const answerFlashcard = (lexemeId: string, seed: string, optionIndex: number) =>
  request<FlashcardResult>("/flashcards/answer", {
    method: "POST",
    body: JSON.stringify({ lexeme_id: lexemeId, seed, option_index: optionIndex }),
  });
