import { API_BASE_URL } from "./api";
import type {
  PlaceDetail,
  SceneStart,
  Submission,
  TurnResult,
  TurnView,
  VillageOverview,
} from "./gameTypes";

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

export function artUrl(artId: string): string {
  return `${API_BASE_URL}/api/game/art/${artId}`;
}

export const getVillage = () => request<VillageOverview>("/game/village");

export const getPlace = (placeId: string) => request<PlaceDetail>(`/game/places/${placeId}`);

export const startScene = (placeId: string, npcId?: string) =>
  request<SceneStart>(`/game/places/${placeId}/scene`, {
    method: "POST",
    body: JSON.stringify({ npc_id: npcId ?? null }),
  });

export const getTurn = (sceneId: string, seed: string, index: number, typed = false) => {
  const query = new URLSearchParams({ seed, typed: String(typed) });
  return request<TurnView>(`/game/scenes/${sceneId}/turns/${index}?${query}`);
};

export const answerTurn = (
  sceneId: string,
  index: number,
  seed: string,
  submission: Submission,
) =>
  request<TurnResult>(`/game/scenes/${sceneId}/turns/${index}`, {
    method: "POST",
    body: JSON.stringify({ seed, submission }),
  });
