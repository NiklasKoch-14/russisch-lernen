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
