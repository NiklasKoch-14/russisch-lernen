import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as speech from "../audio/SpeechContext";
import type { ListeningDialog, ListeningResult } from "../courseTypes";
import * as api from "../listeningApi";
import ListeningView from "./ListeningView";

const gespraech: ListeningDialog = {
  dialog_id: 2,
  next_unit: null,
  seed: "2:jetzt",
  speakers: [
    { name_ru: "Ле́на", name_de: "Lena", voice: "f" },
    { name_ru: "Оле́г", name_de: "Oleg", voice: "m" },
  ],
  lines: [
    { speaker: 0, text: "что ты пьёшь", translit: "što ty p'još'" },
    { speaker: 1, text: "я пью ко́фе", translit: "ja p'ju kófe" },
    { speaker: 0, text: "я пью чай", translit: "ja p'ju čaj" },
  ],
  question_de: "Worum ging es?",
  options_de: ["Um die Arbeit.", "Was die beiden trinken.", "Um den Weg."],
};

const ergebnis: ListeningResult = {
  correct: true,
  correct_index: 1,
  title_de: "Im Café",
  translations_de: ["Was trinkst du?", "Ich trinke Kaffee.", "Ich trinke Tee."],
};

const say = vi.fn().mockResolvedValue(undefined);

const stimme = (available: boolean) =>
  vi.spyOn(speech, "useSpeech").mockReturnValue({
    available,
    source: available ? "server" : "none",
    autoplay: false,
    setAutoplay: vi.fn(),
    say,
    lastError: null,
    activeVoice: null,
  });

/** Abspielen anstossen und warten, bis die Schleife durch ist.
 *
 * Der Knopf wird ausserhalb von `act` gesucht: darin sieht `findBy*` die
 * Aktualisierung nach dem Laden nicht und laeuft in den Zeitablauf.
 */
const abspielen = async () => {
  const knopf = await screen.findByRole("button", { name: /Abspielen/ });
  await act(async () => {
    fireEvent.click(knopf);
  });
};

function renderListening(path = "/hoeren") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ListeningView />
    </MemoryRouter>,
  );
}

describe("ListeningView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    say.mockClear();
    say.mockResolvedValue(undefined);
    stimme(true);
    vi.spyOn(api, "getNextDialog").mockResolvedValue(gespraech);
    vi.spyOn(api, "answerDialog").mockResolvedValue(ergebnis);
  });

  it("zeigt vor der Antwort keinen russischen Text", async () => {
    renderListening();
    expect(await screen.findByText("2 Sprecher · 3 Zeilen")).toBeInTheDocument();
    expect(screen.queryByText("я пью ко́фе")).not.toBeInTheDocument();
    expect(screen.queryByText("Ich trinke Kaffee.")).not.toBeInTheDocument();
  });

  it("spielt die Zeilen nacheinander mit der Stimme des Sprechers", async () => {
    renderListening();
    await abspielen();

    await waitFor(() => expect(say).toHaveBeenCalledTimes(3));
    expect(say.mock.calls.map((call) => call[0])).toEqual([
      "что ты пьёшь",
      "я пью ко́фе",
      "я пью чай",
    ]);
    expect(say.mock.calls.map((call) => call[1].voice)).toEqual(["f", "m", "f"]);
  });

  it("stellt die Frage erst, wenn das Gespräch einmal durch ist", async () => {
    renderListening();
    expect(await screen.findByText(/Die Frage kommt/)).toBeInTheDocument();

    await abspielen();
    expect(await screen.findByText("Worum ging es?")).toBeInTheDocument();
  });

  it("deckt Titel, Transkript und Übersetzung erst nach der Antwort auf", async () => {
    renderListening();
    await abspielen();
    const option = await screen.findByRole("button", { name: "Was die beiden trinken." });
    await act(async () => {
      fireEvent.click(option);
    });

    expect(await screen.findByText("Im Café")).toBeInTheDocument();
    expect(screen.getByText("я пью ко́фе")).toBeInTheDocument();
    expect(screen.getByText("Ich trinke Kaffee.")).toBeInTheDocument();
    expect(api.answerDialog).toHaveBeenCalledWith(2, "2:jetzt", 1);
  });

  it("holt auf Knopfdruck das nächste Gespräch", async () => {
    renderListening();
    await abspielen();
    const option = await screen.findByRole("button", { name: "Was die beiden trinken." });
    await act(async () => {
      fireEvent.click(option);
    });
    const weiter = await screen.findByRole("button", { name: "Nächstes Gespräch" });
    await act(async () => {
      fireEvent.click(weiter);
    });

    await waitFor(() => expect(api.getNextDialog).toHaveBeenCalledTimes(2));
  });

  it("zeigt ohne Stimme sofort Text und Frage", async () => {
    stimme(false);
    renderListening();

    expect(await screen.findByText("я пью ко́фе")).toBeInTheDocument();
    expect(screen.getByText("Worum ging es?")).toBeInTheDocument();
    expect(screen.getByText(/Ohne russische Stimme/)).toBeInTheDocument();
  });

  it("nennt die Einheit, die das erste Gespräch öffnet", async () => {
    vi.spyOn(api, "getNextDialog").mockResolvedValue({
      ...gespraech,
      dialog_id: null,
      next_unit: 12,
    });
    renderListening();

    expect(await screen.findByText(/Einheit 12/)).toBeInTheDocument();
  });

  it("spielt das von der Startseite gewünschte Gespräch", async () => {
    renderListening("/hoeren?gespraech=2");
    await screen.findByText("Hör zu — worum geht es?");
    expect(api.getNextDialog).toHaveBeenCalledWith(2);
  });

  it("führt nach der Antwort zurück zu Heute", async () => {
    renderListening();
    await abspielen();
    const option = await screen.findByRole("button", { name: "Was die beiden trinken." });
    await act(async () => {
      fireEvent.click(option);
    });
    expect(await screen.findByRole("link", { name: "Zurück zu Heute" })).toHaveAttribute("href", "/");
  });

  it("holt danach wieder das übliche nächste Gespräch statt des gewünschten", async () => {
    renderListening("/hoeren?gespraech=2");
    await abspielen();
    const option = await screen.findByRole("button", { name: "Was die beiden trinken." });
    await act(async () => {
      fireEvent.click(option);
    });
    await act(async () => {
      fireEvent.click(await screen.findByRole("button", { name: "Nächstes Gespräch" }));
    });
    await waitFor(() => expect(api.getNextDialog).toHaveBeenLastCalledWith(undefined));
  });
});
