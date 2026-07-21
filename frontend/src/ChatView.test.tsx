import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ChatView from "./ChatView";
import * as api from "./api";

vi.mock("./api");

describe("ChatView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("starts a placement dialog when the profile is unplaced", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "UNPLACED" });
    vi.mocked(api.startPlacement).mockResolvedValue({ session_id: 1, question: "What is your name?" });

    render(<ChatView />);

    await waitFor(() => {
      expect(screen.getByText("What is your name?")).toBeInTheDocument();
    });
  });

  it("sends placement answers and shows the next question", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "UNPLACED" });
    vi.mocked(api.startPlacement).mockResolvedValue({ session_id: 1, question: "What is your name?" });
    vi.mocked(api.answerPlacement).mockResolvedValue({ finished: false, question: "How old are you?" });

    render(<ChatView />);
    await waitFor(() => screen.getByText("What is your name?"));

    fireEvent.change(screen.getByPlaceholderText("Deine Nachricht..."), { target: { value: "Anna" } });
    fireEvent.click(screen.getByText("Senden"));

    await waitFor(() => {
      expect(screen.getByText("How old are you?")).toBeInTheDocument();
    });
    expect(api.answerPlacement).toHaveBeenCalledWith(1, "Anna");
  });

  it("uses practice mode directly when a level is already set", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "B1" });
    vi.mocked(api.sendPracticeTurn).mockResolvedValue({ reply: "Nice to meet you!" });

    render(<ChatView />);
    await waitFor(() => expect(api.getProfile).toHaveBeenCalled());

    fireEvent.change(screen.getByPlaceholderText("Deine Nachricht..."), { target: { value: "Hi there" } });
    fireEvent.click(screen.getByText("Senden"));

    await waitFor(() => {
      expect(screen.getByText("Nice to meet you!")).toBeInTheDocument();
    });
  });
});
