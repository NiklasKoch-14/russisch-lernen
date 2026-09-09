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
  type_in_village: true,
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
    lastError: null,
    activeVoice: null,
      source: "none",
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
    lastError: null,
    activeVoice: null,
      source: "browser",
    });
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.queryByText(/keine russische Stimme/i)).toBeNull());
  });
});

describe("ProfileView bei einem Sprachausgabe-Fehler", () => {
  beforeEach(() => {
    vi.spyOn(api, "getProfile").mockResolvedValue(profile);
    vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
    vi.spyOn(legacyApi, "getLearningPlan").mockResolvedValue(null);
  });

  it("nennt den Fehlercode, statt ihn zu verschlucken", async () => {
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      autoplay: true,
      setAutoplay: vi.fn(),
      say: vi.fn(),
      lastError: "synthesis-failed",
    activeVoice: null,
      source: "browser",
    });
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("heading", { name: /gemeldet: synthesis-failed/ }),
    ).toBeInTheDocument();
  });

  it("schweigt, solange nichts schiefging", async () => {
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      autoplay: true,
      setAutoplay: vi.fn(),
      say: vi.fn(),
      lastError: null,
    activeVoice: null,
      source: "browser",
    });
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.queryByText(/Die Sprachausgabe hat gemeldet/)).toBeNull(),
    );
  });
});

describe("ProfileView zeigt die aktive Stimme", () => {
  beforeEach(() => {
    vi.spyOn(api, "getProfile").mockResolvedValue(profile);
    vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
    vi.spyOn(legacyApi, "getLearningPlan").mockResolvedValue(null);
  });

  const withVoice = (name: string, local: boolean) =>
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      autoplay: true,
      setAutoplay: vi.fn(),
      say: vi.fn(),
      lastError: null,
      activeVoice: { name, lang: "ru-RU", local },
      source: "browser",
    });

  it("nennt Namen und dass die Stimme aus dem Netz kommt", async () => {
    withVoice("Microsoft Dmitry Online", false);
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/Microsoft Dmitry Online/)).toBeInTheDocument();
    expect(screen.getByText(/online — klingt besser/)).toBeInTheDocument();
  });

  it("nennt eine lokale Stimme als lokal", async () => {
    withVoice("Microsoft Irina Desktop", true);
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/lokal installiert/)).toBeInTheDocument();
  });
});

describe("ProfileView beim Ton vom Server", () => {
  beforeEach(() => {
    vi.spyOn(api, "getProfile").mockResolvedValue(profile);
    vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
    vi.spyOn(legacyApi, "getLearningPlan").mockResolvedValue(null);
  });

  it("nennt den eigenen Sprachdienst statt einer Browserstimme", async () => {
    vi.spyOn(speech, "useSpeech").mockReturnValue({
      available: true,
      source: "server",
      autoplay: true,
      setAutoplay: vi.fn(),
      say: vi.fn(),
      lastError: null,
      activeVoice: { name: "Piper", lang: "ru-RU", local: true },
    });
    render(
      <MemoryRouter>
        <ProfileView />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/Piper/)).toBeInTheDocument();
    expect(screen.getByText(/eigener Sprachdienst/)).toBeInTheDocument();
  });
});
