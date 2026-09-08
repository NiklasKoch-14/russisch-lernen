import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../gameApi";
import SceneView from "./SceneView";

const turn = (index: number) => ({
  index,
  turn_count: 2,
  npc_line: { text: "приве́т как дела́", translit: "privét kak delá", audio_text: "приве́т" },
  exercise: {
    id: `bar-01:s1#${index}`,
    type: "build_sentence" as const,
    prompt_de: "Sag, dass es dir gut geht.",
    audio_prompt: false,
    tiles: [
      { index: 0, text: "хорошо́", translit: "chorošó" },
      { index: 1, text: "пло́хо", translit: "plócho" },
    ],
  },
});

const wrong = {
  correct: false,
  solution_text: "хорошо́",
  solution_translit: "chorošó",
  solution_audio: ["хорошо́"],
  explanation_de: "Richtig ist: хорошо́",
  npc_reaction: { text: "извини́те", translit: "izviníte", audio_text: "извини́те" },
  scene_completed: false,
  outro_de: "",
};

const right = { ...wrong, correct: true, explanation_de: "", npc_reaction: null };

function renderScene() {
  return render(
    <MemoryRouter initialEntries={["/dorf/bar/szene/bar-01?seed=s1"]}>
      <Routes>
        <Route path="/dorf/:placeId/szene/:sceneId" element={<SceneView />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SceneView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die Zeile des NPC und die Kacheln", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();
    expect(await screen.findByText("приве́т как дела́")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /хорошо́/ })).toBeInTheDocument();
  });

  it("wiederholt den Zug nach einem Fehler genau einmal", async () => {
    const getTurn = vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    const answerTurn = vi.spyOn(api, "answerTurn").mockResolvedValue(wrong);
    renderScene();

    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));

    expect(await screen.findByText("извини́те")).toBeInTheDocument();
    expect(screen.getByText(/Richtig ist/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Nochmal" }));

    // Nach "Nochmal" ist der Zug wieder offen: keine Rückmeldung mehr, kein
    // "Weiter" und kein zweites "Nochmal" — und es wurde kein neuer Zug geladen.
    expect(getTurn).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("извини́те")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Weiter" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nochmal" })).not.toBeInTheDocument();

    // Der zweite Versuch (wieder falsch) führt direkt zu "Weiter", nie zu einem
    // weiteren "Nochmal" — das beweist, dass wirklich ein zweiter Versuch
    // stattgefunden hat und nicht bloß ein schon vorhandener Knopf übersehen wurde.
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));

    expect(await screen.findByRole("button", { name: "Weiter" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nochmal" })).not.toBeInTheDocument();
    expect(answerTurn).toHaveBeenCalledTimes(2);
  });

  it("geht nach dem zweiten Versuch weiter, auch wenn er falsch war", async () => {
    const getTurn = vi
      .spyOn(api, "getTurn")
      .mockResolvedValueOnce(turn(0))
      .mockResolvedValueOnce(turn(1));
    vi.spyOn(api, "answerTurn").mockResolvedValue(wrong);
    renderScene();

    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Nochmal" }));
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));

    expect(getTurn).toHaveBeenCalledTimes(2);
  });

  it("zeigt am Ende das Nachwort", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(1));
    vi.spyOn(api, "answerTurn").mockResolvedValue({
      ...right,
      scene_completed: true,
      outro_de: "Pjotr nickt.",
    });
    renderScene();
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(await screen.findByText("Pjotr nickt.")).toBeInTheDocument();
  });
});
