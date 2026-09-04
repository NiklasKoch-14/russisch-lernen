import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../courseApi";
import CourseView from "./CourseView";

const overview = {
  stages: [
    {
      stage: 0,
      units: [
        {
          id: 1,
          title_de: "Buchstaben, die täuschen",
          scenario_de: "…",
          status: "completed" as const,
          correct_count: 6,
          exercise_count: 6,
        },
      ],
    },
    {
      stage: 1,
      units: [
        {
          id: 5,
          title_de: "Hallo und tschüss",
          scenario_de: "…",
          status: "not_started" as const,
          correct_count: 0,
          exercise_count: 7,
        },
      ],
    },
  ],
};

describe("CourseView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die Stufen mit ihren Überschriften", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue(overview);
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    expect(await screen.findByText("Schrift & Klang")).toBeInTheDocument();
    expect(screen.getByText("Erste Sätze")).toBeInTheDocument();
  });

  it("verlinkt jede Einheit", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue(overview);
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    const link = await screen.findByRole("link", { name: /Hallo und tschüss/ });
    expect(link).toHaveAttribute("href", "/kurs/5");
  });

  it("markiert abgeschlossene Einheiten", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue(overview);
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    expect(
      await screen.findByLabelText(/Einheit 1: .+ — abgeschlossen/),
    ).toBeInTheDocument();
  });

  it("zeigt eine deutsche Fehlermeldung, wenn das Laden scheitert", async () => {
    vi.spyOn(api, "getCourse").mockRejectedValue(new Error("kaputt"));
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    expect(await screen.findByText(/konnte nicht geladen werden/i)).toBeInTheDocument();
  });
});
