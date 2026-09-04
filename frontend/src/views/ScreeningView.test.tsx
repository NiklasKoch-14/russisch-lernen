import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../courseApi";
import ScreeningView from "./ScreeningView";

const probe = {
  id: "s1",
  index: 0,
  total: 6,
  prompt_de: "Welcher Buchstabe klingt wie ein gerolltes r?",
  options: ["Р", "П", "Г"],
};

function renderScreening() {
  return render(
    <MemoryRouter>
      <ScreeningView />
    </MemoryRouter>,
  );
}

describe("ScreeningView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die erste Sonde mit Fortschritt", async () => {
    vi.spyOn(api, "startScreening").mockResolvedValue({ finished: false, probe });
    renderScreening();
    expect(await screen.findByText(probe.prompt_de)).toBeInTheDocument();
    expect(screen.getByText("Frage 1 von 6")).toBeInTheDocument();
  });

  it("schickt die gesammelten Antworten weiter", async () => {
    vi.spyOn(api, "startScreening").mockResolvedValue({ finished: false, probe });
    const answer = vi
      .spyOn(api, "answerScreening")
      .mockResolvedValue({ finished: false, probe: { ...probe, index: 1 } });
    renderScreening();
    fireEvent.click(await screen.findByRole("button", { name: "П" }));
    expect(answer).toHaveBeenCalledWith([1]);
  });

  it("zeigt am Ende die empfohlene Starteinheit", async () => {
    vi.spyOn(api, "startScreening").mockResolvedValue({ finished: false, probe });
    vi.spyOn(api, "answerScreening").mockResolvedValue({ finished: true, placement_unit: 5 });
    renderScreening();
    fireEvent.click(await screen.findByRole("button", { name: "Р" }));
    expect(await screen.findByRole("link", { name: /Einheit 5/ })).toHaveAttribute(
      "href",
      "/kurs/5",
    );
  });

  it("meldet einen Fehler auf Deutsch", async () => {
    vi.spyOn(api, "startScreening").mockRejectedValue(new Error("kaputt"));
    renderScreening();
    expect(await screen.findByText(/konnte nicht geladen werden/i)).toBeInTheDocument();
  });
});
