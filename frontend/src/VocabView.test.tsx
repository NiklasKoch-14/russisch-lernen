import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VocabView from "./VocabView";
import * as api from "./api";

vi.mock("./api");

describe("VocabView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows a message when no cards are due", async () => {
    vi.mocked(api.getDueCards).mockResolvedValue([]);

    render(<VocabView />);

    await waitFor(() => {
      expect(screen.getByText("Keine fälligen Karteikarten.")).toBeInTheDocument();
    });
  });

  it("shows the term, then feedback after submitting an answer", async () => {
    vi.mocked(api.getDueCards).mockResolvedValue([
      { id: 1, term: "house", translation: "Haus", example_sentence: "x", due_date: "2026-07-21" },
    ]);
    vi.mocked(api.answerVocabCard).mockResolvedValue({ correct: true });

    render(<VocabView />);
    await waitFor(() => screen.getByText("house"));

    fireEvent.change(screen.getByPlaceholderText("Übersetzung eingeben..."), {
      target: { value: "Haus" },
    });
    fireEvent.click(screen.getByText("Prüfen"));

    await waitFor(() => {
      expect(screen.getByText("Richtig!")).toBeInTheDocument();
    });
    expect(api.answerVocabCard).toHaveBeenCalledWith(1, "Haus");
  });

  it("shows the correct translation and advances after an incorrect answer", async () => {
    vi.mocked(api.getDueCards).mockResolvedValue([
      { id: 1, term: "house", translation: "Haus", example_sentence: "x", due_date: "2026-07-21" },
    ]);
    vi.mocked(api.answerVocabCard).mockResolvedValue({ correct: false });

    render(<VocabView />);
    await waitFor(() => screen.getByText("house"));

    fireEvent.change(screen.getByPlaceholderText("Übersetzung eingeben..."), {
      target: { value: "Katze" },
    });
    fireEvent.click(screen.getByText("Prüfen"));

    await waitFor(() => {
      expect(screen.getByText("Falsch. Richtig wäre: Haus")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Weiter"));
    expect(screen.getByText("Alle fälligen Karten erledigt!")).toBeInTheDocument();
  });
});
