import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import * as api from "./courseApi";

vi.mock("./ChatView", () => ({ default: () => <div>ChatView</div> }));
vi.mock("./ProfileView", () => ({ default: () => <div>ProfileView</div> }));

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
    vi.spyOn(api, "getProfile").mockResolvedValue({
      language: "russian",
      cefr_level: "UNPLACED",
      show_transliteration: true,
      audio_autoplay: true,
      placement_unit: null,
    });
  });

  it("zeigt die Hauptnavigation", () => {
    render(
      <MemoryRouter initialEntries={["/kurs"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Kurs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Wiederholen" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Profil" })).toBeInTheDocument();
  });

  it("führt das freie Gespräch nicht in der Hauptnavigation", () => {
    render(
      <MemoryRouter initialEntries={["/kurs"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("link", { name: /Gespräch/ })).not.toBeInTheDocument();
  });

  it("öffnet das Profil über seine Route", () => {
    render(
      <MemoryRouter initialEntries={["/profil"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText("ProfileView")).toBeInTheDocument();
  });
});
