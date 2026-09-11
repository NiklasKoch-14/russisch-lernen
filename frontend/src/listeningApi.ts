import { API_BASE_URL } from "./api";
import type { ListeningDialog, ListeningResult } from "./courseTypes";

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

/** Das nächste Gespräch — oder genau dieses, wenn die Startseite es vorschlägt. */
export const getNextDialog = (dialogId?: number) =>
  request<ListeningDialog>(
    dialogId === undefined ? "/listening/next" : `/listening/next?dialog_id=${dialogId}`,
  );

export const answerDialog = (dialogId: number, seed: string, optionIndex: number) =>
  request<ListeningResult>(`/listening/${dialogId}/answer`, {
    method: "POST",
    body: JSON.stringify({ seed, option_index: optionIndex }),
  });
