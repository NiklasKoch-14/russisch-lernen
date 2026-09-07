import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as legacyApi from "./api";
import * as speech from "./audio/SpeechContext";
import * as api from "./courseApi";
import ProfileView from "./ProfileView";

const profile = {
  language: "russian",
  cefr_level: "B1",
  show_transliteration: true,
  audio_autoplay: true,
  placement_unit: 5,
};

function renderProfile() {
  return render(
    <MemoryRouter>
      <ProfileView />
    </MemoryRouter>,
  );
}

describe("ProfileView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "getProfile").mockResolvedValue(profile);
    vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
    vi.spyOn(legacyApi, "getLearningPlan").mockResolvedValue(null);
  });

  it("zeigt Level und empfohlenen Einstieg", async () => {
    renderProfile();
    await waitFor(() => expect(screen.getByText("Aktuelles Level: B1")).toBeInTheDocument());
    expect(screen.getByText("Empfohlener Einstieg: Einheit 5")).toBeInTheDocument();
  });

  it("zeigt einen Platzhalter, wenn es noch keinen Lernplan gibt", async () => {
    renderProfile();
    await waitFor(() =>
      expect(screen.getByText("Noch kein Lernplan vorhanden.")).toBeInTheDocument(),
    );
  });

  it("bietet einen Schalter für die Umschrift", async () => {
    renderProfile();
    expect(screen.getByLabelText("Umschrift anzeigen")).toBeInTheDocument();
  });

  it("verlinkt die Einstufung", async () => {
    renderProfile();
    expect(screen.getByRole("link", { name: "Einstufung starten" })).toHaveAttribute(
      "href",
      "/einstufung",
    );
  });

  it("blendet das freie Gespräch vor Stufe 3 aus", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue({
      stages: [
        {
          stage: 1,
          units: [
            {
              id: 5,
              title_de: "x",
              scenario_de: "y",
              status: "completed" as const,
              correct_count: 7,
              exercise_count: 7,
            },
          ],
        },
      ],
    });
    renderProfile();
    expect(await screen.findByText(/schaltet sich frei/i)).toBeInTheDocument();
  });

  it("schaltet das freie Gespräch ab Stufe 3 frei", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue({
      stages: [
        {
          stage: 3,
          units: [
            {
              id: 53,
              title_de: "x",
              scenario_de: "y",
              status: "completed" as const,
              correct_count: 8,
              exercise_count: 8,
            },
          ],
        },
      ],
    });
    renderProfile();
    expect(await screen.findByRole("link", { name: "Freies Gespräch öffnen" })).toBeInTheDocument();
  });
});

describe("ProfileView ohne russische Stimme", () => {
  beforeEach(() => {
    vi.spyOn(api, "getProfile").mockResolvedValue(profile);
    vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
    vi.spyOn(legacyApi, "getLearningPlan").mockResolvedValue(null);
  });

  it("erklärt, was zu tun ist, wenn keine russische Stimme da ist", async () => {
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: false,
      autoplay: true,
      setAutoplay: vi.fn(),
      say: vi.fn(),
    });
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/keine russische Stimme/i)).toBeInTheDocument();
  });

  it("schweigt, wenn eine Stimme vorhanden ist", async () => {
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      autoplay: true,
      setAutoplay: vi.fn(),
      say: vi.fn(),
    });
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.queryByText(/keine russische Stimme/i)).toBeNull());
  });
});
