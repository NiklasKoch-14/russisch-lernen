import type { BuildSentenceExercise, Submission } from "./courseTypes";

export interface Hotspot {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Place {
  id: string;
  name_ru: string;
  name_de: string;
  kind: "course" | "npcs" | "shopping";
  art: string;
  hotspot: Hotspot;
}

export interface VillageOverview {
  places: Place[];
}

export interface Npc {
  id: string;
  name_ru: string;
  name_de: string;
  about_de: string;
  art: string;
}

export interface PlaceDetail {
  id: string;
  name_ru: string;
  name_de: string;
  kind: Place["kind"];
  art: string;
  npcs: Npc[];
  next_unit_id?: number | null;
}

export interface SceneStart {
  scene_id: string;
  seed: string;
  title_de: string;
  intro_de: string;
  hint_unit: number;
  npc: { id: string; name_ru: string; name_de: string; art: string };
  turn_count: number;
}

export interface SpokenLine {
  text: string;
  translit: string;
  audio_text: string;
}

export interface TurnView {
  index: number;
  turn_count: number;
  npc_line: SpokenLine;
  exercise: BuildSentenceExercise;
}

export interface TurnResult {
  correct: boolean;
  solution_text: string;
  solution_translit: string;
  solution_audio: string[];
  explanation_de: string;
  npc_reaction: SpokenLine | null;
  scene_completed: boolean;
  outro_de: string;
}

export type { Submission };
