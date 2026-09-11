import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as courseApi from "../courseApi";
import * as api from "../gameApi";
import SceneView from "./SceneView";

const bar = {
  id: "bar",
  name_ru: "бар",
  name_de: "Bar",
  kind: "npcs" as const,
  art: "bar",
  npcs: [
    {
      id: "pjotr",
      name_ru: "Пётр",
      name_de: "Pjotr",
      about_de: "Sitzt jeden Abend am selben Platz.",
      art: "npc_pjotr",
      spot: { x: 0.03, y: 0.36, w: 0.14, h: 0.42 },
    },
    {
      id: "nadja",
      name_ru: "На́дя",
      name_de: "Nadja",
      about_de: "Steht hinter der Theke.",
      art: "npc_nadja",
      spot: { x: 0.8, y: 0.25, w: 0.13, h: 0.29 },
    },
  ],
};

const turn = (index: number) => ({
  index,
  turn_count: 2,
  npc: { id: "pjotr", name_ru: "Пётр", name_de: "Pjotr", art: "npc_pjotr" },
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
  wrong_word_index: null,
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
        <Route path="/dorf/:placeId" element={<p>Zurück im Raum</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

const profile = {
  language: "russian",
  cefr_level: "A1",
  show_transliteration: true,
  type_in_village: false,
  placement_unit: null,
  audio_autoplay: true,
};

const typingTurn = (index: number) => ({
  ...turn(index),
  exercise: {
    id: `bar-01:s1#${index}`,
    type: "type_sentence" as const,
    prompt_de: "Sag, dass es dir gut geht.",
    word_count: 1,
  },
});

describe("SceneView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Der Kachelmodus ist hier die Vorgabe, damit die alten Faelle unveraendert
    // gelten; das Tippen bekommt eigene Faelle.
    vi.spyOn(courseApi, "getProfile").mockResolvedValue(profile);
    vi.spyOn(courseApi, "patchProfile").mockResolvedValue(profile);
  });

  it("zeigt die Zeile des NPC und die Kacheln", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();
    expect(await screen.findByText("приве́т как дела́")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /хорошо́/ })).toBeInTheDocument();
  });

  it("zeigt in der Karte, mit wem man spricht", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();
    const card = await screen.findByTestId("dialog-card");
    expect(within(card).getByText("Пётр")).toBeInTheDocument();
    expect(within(card).getByText("Pjotr")).toBeInTheDocument();
  });

  it("laesst den Raum stehen und hebt die angesprochene Person hervor", async () => {
    const getPlace = vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();

    expect(await screen.findByTestId("place-stage")).toBeInTheDocument();
    expect(getPlace).toHaveBeenCalledWith("bar");
    expect(screen.getByTestId("figure-pjotr").className).not.toMatch(/opacity-/);
    expect(screen.getByTestId("figure-nadja").className).toMatch(/opacity-/);
  });

  it("laesst waehrend des Gespraechs niemanden im Raum anklicken", async () => {
    // Ein halb gefuehrtes Gespraech soll nicht durch einen Klick verlorengehen.
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();
    await screen.findByTestId("place-stage");
    expect(screen.queryByRole("button", { name: /На́дя/ })).not.toBeInTheDocument();
  });

  it("legt die Karte auf die Seite, wo mehr Platz ist", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    const { unmount } = renderScene();
    // Pjotr steht links im Bild — die Karte gehoert nach rechts.
    expect(await screen.findByTestId("dialog-card")).toHaveAttribute("data-side", "right");
    unmount();

    vi.spyOn(api, "getTurn").mockResolvedValue({
      ...turn(0),
      npc: { id: "nadja", name_ru: "На́дя", name_de: "Nadja", art: "npc_nadja" },
    });
    renderScene();
    expect(await screen.findByTestId("dialog-card")).toHaveAttribute("data-side", "left");
  });

  it("bricht auf Wunsch ab und geht zurueck in den Raum", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();
    fireEvent.click(await screen.findByRole("button", { name: "Zurück" }));
    expect(await screen.findByText("Zurück im Raum")).toBeInTheDocument();
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

  it("bestaetigt eine richtige Antwort sichtbar", async () => {
    // Ohne Rueckmeldung weiss man nach dem Pruefen nicht, ob es gestimmt hat —
    // im Kurs steht dort seit jeher "Richtig!" auf gruenem Grund.
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    vi.spyOn(api, "answerTurn").mockResolvedValue(right);
    renderScene();
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));

    const feedback = await screen.findByTestId("turn-feedback");
    expect(within(feedback).getByText("Richtig!")).toBeVisible();
    expect(feedback.className).toMatch(/emerald/);
  });

  it("benennt eine falsche Antwort als solche", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    vi.spyOn(api, "answerTurn").mockResolvedValue(wrong);
    renderScene();
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));

    const feedback = await screen.findByTestId("turn-feedback");
    expect(within(feedback).getByText("Nicht ganz.")).toBeVisible();
    expect(feedback.className).toMatch(/rose/);
  });

  it("stellt den Ortsnamen der Karte gegenueber", async () => {
    // Steht die Karte links, gehoert der Name nach rechts — sonst deckt sie
    // ihn zu.
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    vi.spyOn(api, "getTurn").mockResolvedValue({
      ...turn(0),
      npc: { id: "nadja", name_ru: "На́дя", name_de: "Nadja", art: "npc_nadja" },
    });
    renderScene();
    expect(await screen.findByTestId("dialog-card")).toHaveAttribute("data-side", "left");
    const header = screen.getByTestId("place-header").parentElement!.parentElement!;
    expect(header.className).toMatch(/right-4/);
    expect(header.className).not.toMatch(/left-4/);
  });

  it("nennt ueber dem Raum, wo man ist", async () => {
    // Derselbe Kopf wie auf der Ortsseite — sonst wechselt beim Ansprechen
    // einer Person die halbe Seitengestalt.
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();
    const header = await screen.findByTestId("place-header");
    expect(within(header).getByText("бар")).toBeVisible();
    expect(within(header).getByText("Bar")).toBeVisible();
  });

  it("behaelt die gewaehlte Kachel, wenn der Raum erst spaeter eintrifft", async () => {
    // Der Raum wird getrennt geladen. Haengt React die Dialogkarte beim
    // Eintreffen um, verliert die Aufgabe ihre Auswahl — genau das ist beim
    // Umbau auf das Vollbild passiert.
    let liefereRaum: (place: typeof bar) => void = () => {};
    vi.spyOn(api, "getPlace").mockReturnValue(
      new Promise((resolve) => {
        liefereRaum = resolve;
      }) as ReturnType<typeof api.getPlace>,
    );
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();

    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    expect(screen.getByRole("button", { name: /хорошо́/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await act(async () => {
      liefereRaum(bar);
    });

    await screen.findByTestId("place-stage");
    expect(screen.getByRole("button", { name: /хорошо́/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
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

describe("SceneView — tippen statt klicken", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(courseApi, "getProfile").mockResolvedValue({ ...profile, type_in_village: true });
    vi.spyOn(courseApi, "patchProfile").mockResolvedValue(profile);
  });

  it("holt den Zug in der Form, die das Profil vorgibt", async () => {
    const getTurn = vi.spyOn(api, "getTurn").mockResolvedValue(typingTurn(0));
    renderScene();
    await screen.findByLabelText("Deine Antwort auf Russisch");
    expect(getTurn).toHaveBeenCalledWith("bar-01", "s1", 0, true);
  });

  it("schickt den getippten Satz statt Kachelnummern", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(typingTurn(0));
    const answerTurn = vi.spyOn(api, "answerTurn").mockResolvedValue(right);
    renderScene();
    const field = await screen.findByLabelText("Deine Antwort auf Russisch");
    fireEvent.change(field, { target: { value: "хорошо" } });
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(answerTurn).toHaveBeenCalledWith("bar-01", 0, "s1", { text: "хорошо" });
  });

  it("markiert nach der Antwort das beanstandete Wort", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(typingTurn(0));
    vi.spyOn(api, "answerTurn").mockResolvedValue({ ...wrong, wrong_word_index: 0 });
    renderScene();
    const field = await screen.findByLabelText("Deine Antwort auf Russisch");
    fireEvent.change(field, { target: { value: "пло́хо" } });
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));

    const shown = await screen.findByTestId("typed-answer");
    expect(shown.querySelector("span")?.className).toContain("rose");
  });

  it("stellt auf Wunsch auf Kacheln zurueck und merkt sich das", async () => {
    const getTurn = vi
      .spyOn(api, "getTurn")
      .mockResolvedValueOnce(typingTurn(0))
      .mockResolvedValue(turn(0));
    const patch = vi.spyOn(courseApi, "patchProfile").mockResolvedValue(profile);
    renderScene();

    fireEvent.click(await screen.findByRole("button", { name: "lieber Kacheln" }));
    expect(await screen.findByRole("button", { name: /хорошо́/ })).toBeInTheDocument();
    expect(getTurn).toHaveBeenLastCalledWith("bar-01", "s1", 0, false);
    expect(patch).toHaveBeenCalledWith({ type_in_village: false });
  });

  it("bietet den Wechsel nach dem Pruefen nicht mehr an", async () => {
    // Sonst passte die Aufgabe nicht mehr zu der Rueckmeldung darunter.
    vi.spyOn(api, "getTurn").mockResolvedValue(typingTurn(0));
    vi.spyOn(api, "answerTurn").mockResolvedValue(right);
    renderScene();
    const field = await screen.findByLabelText("Deine Antwort auf Russisch");
    fireEvent.change(field, { target: { value: "хорошо" } });
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));

    await screen.findByTestId("turn-feedback");
    expect(screen.queryByRole("button", { name: "lieber Kacheln" })).not.toBeInTheDocument();
  });

  it("bietet nach dem Ende der Szene den Weg zurück zu Heute an", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    vi.spyOn(api, "answerTurn").mockResolvedValue({
      ...right,
      scene_completed: true,
      outro_de: "Pjotr nickt.",
    });
    renderScene();
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));
    expect(await screen.findByText("Geschafft!")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Zurück zu Heute" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("button", { name: "Zurück in den Raum" })).toBeInTheDocument();
  });
});
