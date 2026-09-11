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

/** Das Gespräch als eine fertig geladene Tonspur. */
export interface DialogTrack {
  /** Blob-URL — der Aufrufer gibt sie mit `URL.revokeObjectURL` wieder frei. */
  url: string;
  /** Wann jede Zeile beginnt, in Sekunden. */
  starts: number[];
}

/**
 * Lädt das ganze Gespräch als eine Datei, bevor es spielt. Aus einem fertigen
 * Blob gespielt, reißt nichts ab, und die Länge steht vorab fest.
 */
export async function loadDialogTrack(dialogId: number): Promise<DialogTrack> {
  const response = await fetch(`${API_BASE_URL}/api/listening/${dialogId}/audio`);
  if (!response.ok) throw new Error(`Tonspur nicht verfügbar: ${response.status}`);
  const starts = (response.headers.get("X-Line-Starts") ?? "")
    .split(",")
    .filter((value) => value.trim() !== "")
    .map(Number);
  const blob = await response.blob();
  return { url: URL.createObjectURL(blob), starts };
}
