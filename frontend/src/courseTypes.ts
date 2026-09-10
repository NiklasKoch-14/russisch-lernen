export interface Word {
  text: string;
  translit: string;
  /** Fehlt, wo die Bedeutung die Lösung wäre — Paare zuordnen, Hörverstehen. */
  gloss_de?: string;
}

export interface Tile extends Word {
  index: number;
}

export interface GlossOption {
  index: number;
  gloss_de: string;
}

export interface BuildSentenceExercise {
  id: string;
  type: "build_sentence";
  prompt_de: string;
  tiles: Tile[];
  audio_prompt: boolean;
  audio_text?: string;
}

export interface ChooseFormExercise {
  id: string;
  type: "choose_form";
  prompt_de: string;
  sentence: (Word | null)[];
  options: Tile[];
  audio_prompt: boolean;
  audio_text?: string;
}

export interface MatchPairsExercise {
  id: string;
  type: "match_pairs";
  prompt_de: string;
  left: Tile[];
  right: GlossOption[];
}

export interface DialogReplyExercise {
  id: string;
  type: "dialog_reply";
  prompt_de: string;
  tutor_line: Word[];
  options: Tile[];
}

export interface ListenMeaningExercise {
  id: string;
  type: "listen_meaning";
  prompt_de: string;
  audio_text: string;
  sentence: Word[];
  options_de: string[];
}

export interface TypeSentenceExercise {
  id: string;
  type: "type_sentence";
  prompt_de: string;
  /** Wie viele Wörter gesucht sind — ohne die Angabe rät man beim Auftrag. */
  word_count: number;
}

export type Exercise =
  | BuildSentenceExercise
  | ChooseFormExercise
  | MatchPairsExercise
  | DialogReplyExercise
  | ListenMeaningExercise
  | TypeSentenceExercise;

export type Submission =
  | { tile_indices: number[] }
  | { option_index: number }
  | { pairs: number[][] }
  | { text: string };

export interface NewWord extends Word {
  id: string;
  gloss_de: string;
}

export interface Primer {
  id: string;
  title_de: string;
  text_de: string;
  /** Wahr in der Einheit, die den Begriff zuerst benutzt — dort steht der Kasten offen. */
  first_use: boolean;
}

export interface UnitDetail {
  id: number;
  stage: number;
  title_de: string;
  scenario_de: string;
  grammar_focus: { id: string; title_de: string; explanation_de: string };
  primer: Primer | null;
  new_words: NewWord[];
  solved_exercise_ids: string[];
  exercises: Exercise[];
}

export interface UnitSummary {
  id: number;
  title_de: string;
  scenario_de: string;
  status: "not_started" | "in_progress" | "completed";
  correct_count: number;
  exercise_count: number;
}

export interface CourseOverview {
  stages: { stage: number; units: UnitSummary[] }[];
}

export interface AnswerResult {
  correct: boolean;
  solution_text: string;
  solution_translit: string;
  solution_audio: string[];
  explanation_de: string;
  unit_completed: boolean;
  correct_count: number;
  total_count: number;
}

export interface ScreeningProbe {
  id: string;
  index: number;
  total: number;
  prompt_de: string;
  options: string[];
}

export type ScreeningStep =
  | { finished: false; probe: ScreeningProbe }
  | { finished: true; placement_unit: number };

export interface ReviewPairsItem {
  kind: "pairs";
  left: (Tile & { ref: string })[];
  right: GlossOption[];
}

export type ReviewExerciseItem = {
  kind: "exercise";
  unit_id: number;
  exercise_id: string;
  ref: string;
} & Exercise;

export type ReviewItem = ReviewExerciseItem | ReviewPairsItem;

export interface ReviewRound {
  items: ReviewItem[];
}

export interface ReviewResult {
  correct_count: number;
  total_count: number;
  results: { ref: string; correct: boolean; gloss_de: string; text: string }[];
}

export interface Profile {
  language: string;
  cefr_level: string;
  show_transliteration: boolean;
  /** Im Dorf wird getippt statt geklickt. */
  type_in_village: boolean;
  placement_unit: number | null;
  audio_autoplay: boolean;
}

/** Wer im Hörgespräch spricht. `voice` waehlt das Stimmmodell auf dem Server. */
export interface ListeningSpeaker {
  name_ru: string;
  name_de: string;
  voice: "m" | "f";
}

export interface ListeningLine {
  speaker: number;
  text: string;
  translit: string;
}

/**
 * Ein Hörgespräch, wie es beim Client ankommt: genug zum Hören, nichts zum
 * Antworten. `dialog_id: null` heisst, dass noch keine Einheit weit genug ist —
 * dann sagt `next_unit`, welche das erste Gespräch öffnet.
 */
export interface ListeningDialog {
  dialog_id: number | null;
  next_unit: number | null;
  seed: string;
  speakers: ListeningSpeaker[];
  lines: ListeningLine[];
  question_de: string;
  options_de: string[];
}

export interface ListeningResult {
  correct: boolean;
  correct_index: number;
  title_de: string;
  translations_de: string[];
}
