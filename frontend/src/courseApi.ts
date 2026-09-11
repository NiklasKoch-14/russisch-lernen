import { API_BASE_URL } from "./api";
import type {
  AnswerResult,
  CourseOverview,
  Profile,
  ReviewResult,
  ReviewRound,
  ScreeningStep,
  Submission,
  TodayPlan,
  UnitDetail,
} from "./courseTypes";

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

export const getCourse = () => request<CourseOverview>("/course");

export const getToday = () => request<TodayPlan>("/today");

export const getUnit = (unitId: number) => request<UnitDetail>(`/units/${unitId}`);

export const submitAnswer = (unitId: number, exerciseId: string, submission: Submission) =>
  request<AnswerResult>(`/units/${unitId}/answer`, {
    method: "POST",
    body: JSON.stringify({ exercise_id: exerciseId, submission }),
  });

export const startScreening = () => request<ScreeningStep>("/screening/start", { method: "POST" });

export const answerScreening = (answers: number[]) =>
  request<ScreeningStep>("/screening/answer", {
    method: "POST",
    body: JSON.stringify({ answers }),
  });

export const getReviewRound = () => request<ReviewRound>("/review/due");

export const submitReviewRound = (pairs: number[][]) =>
  request<ReviewResult>("/review/answer", {
    method: "POST",
    body: JSON.stringify({ pairs }),
  });

/** Eine echte Kursaufgabe in der Wiederholung — ohne Wirkung auf den Einheiten-Fortschritt. */
export const submitReviewExercise = (
  unitId: number,
  exerciseId: string,
  submission: Submission,
) =>
  request<AnswerResult>("/review/exercise", {
    method: "POST",
    body: JSON.stringify({ unit_id: unitId, exercise_id: exerciseId, submission }),
  });

export const getProfile = () => request<Profile>("/profile");

export const patchProfile = (
  patch: Partial<Pick<Profile, "show_transliteration" | "audio_autoplay" | "type_in_village">>,
) =>
  request<Profile>("/profile", { method: "PATCH", body: JSON.stringify(patch) });
