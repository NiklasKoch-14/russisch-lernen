import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfileView from "./ProfileView";
import * as api from "./api";

vi.mock("./api");

describe("ProfileView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows the current level and learning plan topics", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "B1" });
    vi.mocked(api.getLearningPlan).mockResolvedValue({ topics: ["Ordering food", "Small talk"] });

    render(<ProfileView />);

    await waitFor(() => {
      expect(screen.getByText("Aktuelles Level: B1")).toBeInTheDocument();
    });
    expect(screen.getByText("Ordering food")).toBeInTheDocument();
    expect(screen.getByText("Small talk")).toBeInTheDocument();
  });

  it("shows a placeholder when no learning plan exists yet", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "UNPLACED" });
    vi.mocked(api.getLearningPlan).mockResolvedValue(null);

    render(<ProfileView />);

    await waitFor(() => {
      expect(screen.getByText("Noch kein Lernplan vorhanden.")).toBeInTheDocument();
    });
  });
});
