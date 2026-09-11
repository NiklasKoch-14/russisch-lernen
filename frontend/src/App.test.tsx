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
    vi.spyOn(api, "getToday").mockResolvedValue({
      greeting: "normal",
      steps: [],
      unit_skipped: null,
      next_unit_id: 1,
      finished: false,
      week_days: 0,
      offer_screening: false,
    });
    vi.spyOn(api, "getProfile").mockResolvedValue({
      language: "russian",
      cefr_level: "UNPLACED",
      show_transliteration: true,
      type_in_village: true,
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

  it("beginnt mit der Startseite Heute", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    const tabs = screen.getAllByRole("link").map((link) => link.textContent);
    expect(tabs[0]).toBe("Heute");
    expect(screen.getByRole("link", { name: "Heute" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByRole("heading", { name: "Heute" })).toBeInTheDocument();
  });

  it("markiert Heute nicht, wenn man im Kurs ist", () => {
    render(
      <MemoryRouter initialEntries={["/kurs"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Heute" })).not.toHaveAttribute("aria-current");
  });
});
