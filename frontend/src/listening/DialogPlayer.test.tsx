import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as speech from "../audio/SpeechContext";
import { SLOW_PLAYBACK_RATE } from "../audio/serverSpeech";
import type { ListeningLine, ListeningSpeaker } from "../courseTypes";
import * as api from "../listeningApi";
import DialogPlayer from "./DialogPlayer";

const speakers: ListeningSpeaker[] = [
  { name_ru: "Пётр", name_de: "Pjotr", voice: "m" },
  { name_ru: "На́дя", name_de: "Nadja", voice: "f" },
];
const lines: ListeningLine[] = [
  { speaker: 0, text: "приве́т", translit: "privét" },
  { speaker: 1, text: "приве́т как дела́", translit: "privét kak delá" },
  { speaker: 0, text: "хорошо́", translit: "chorošó" },
];

/** Die Tonspur im Test: spielt nur, wenn der Test die Zeit vorrückt. */
class FakeTrack {
  static last: FakeTrack | null = null;
  src: string;
  currentTime = 0;
  duration = Number.NaN;
  playbackRate = 1;
  preservesPitch = false;
  paused = true;
  ended = false;
  play = vi.fn(() => {
    this.paused = false;
    this.ended = false;
    this.fire("play");
    return Promise.resolve();
  });
  pause = vi.fn(() => {
    this.paused = true;
    this.fire("pause");
  });
  private handlers: Record<string, (() => void)[]> = {};

  constructor(src: string) {
    this.src = src;
    FakeTrack.last = this;
  }

  addEventListener(type: string, handler: () => void) {
    (this.handlers[type] ??= []).push(handler);
  }

  fire(type: string) {
    (this.handlers[type] ?? []).forEach((handler) => handler());
  }

  /** Wie der Browser: Länge bekannt, dann läuft die Zeit. */
  load(seconds: number) {
    this.duration = seconds;
    this.fire("loadedmetadata");
  }

  at(seconds: number) {
    this.currentTime = seconds;
    this.fire("timeupdate");
  }

  finish() {
    this.currentTime = this.duration;
    this.paused = true;
    this.ended = true;
    this.fire("timeupdate");
    this.fire("ended");
  }
}

const say = vi.fn();

function voice(source: "server" | "browser") {
  vi.spyOn(speech, "useSpeech").mockReturnValue({
    available: true,
    source,
    autoplay: false,
    setAutoplay: vi.fn(),
    say,
    lastError: null,
    activeVoice: null,
  });
}

function renderPlayer(onFinished = vi.fn()) {
  render(<DialogPlayer dialogId={7} speakers={speakers} lines={lines} onFinished={onFinished} />);
  return onFinished;
}

/** Den Player bis zur spielbereiten Spur bringen. */
async function loaded(seconds = 10) {
  const button = await screen.findByRole("button", { name: /Abspielen/ });
  act(() => FakeTrack.last!.load(seconds));
  return button;
}

beforeEach(() => {
  vi.restoreAllMocks();
  say.mockReset();
  say.mockResolvedValue(undefined);
  FakeTrack.last = null;
  vi.stubGlobal("Audio", FakeTrack);
  vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(), revokeObjectURL: vi.fn() });
});

afterEach(() => {
  // Erst abbauen, dann die Attrappen wegnehmen — beim Abbau gibt der Player
  // die Blob-URL frei, und jsdom kennt URL.revokeObjectURL nicht.
  cleanup();
  vi.unstubAllGlobals();
});

describe("DialogPlayer mit Tonspur vom Server", () => {
  beforeEach(() => {
    voice("server");
    vi.spyOn(api, "loadDialogTrack").mockResolvedValue({
      url: "blob:gespraech",
      starts: [0, 2.5, 5],
    });
  });

  it("lädt das ganze Gespräch vor, bevor es sich abspielen lässt", async () => {
    let fertig: (value: { url: string; starts: number[] }) => void = () => {};
    vi.spyOn(api, "loadDialogTrack").mockReturnValue(
      new Promise((resolve) => {
        fertig = resolve;
      }),
    );
    renderPlayer();
    expect(screen.getByRole("button", { name: "Gespräch wird geladen …" })).toBeDisabled();

    await act(async () => fertig({ url: "blob:gespraech", starts: [0, 2.5, 5] }));
    expect(screen.getByRole("button", { name: /Abspielen/ })).toBeEnabled();
    expect(api.loadDialogTrack).toHaveBeenCalledWith(7);
    expect(FakeTrack.last!.src).toBe("blob:gespraech");
  });

  it("spielt eine Spur statt einzelner Sätze", async () => {
    renderPlayer();
    fireEvent.click(await loaded());
    expect(FakeTrack.last!.play).toHaveBeenCalled();
    expect(say).not.toHaveBeenCalled();
  });

  it("zeigt, wie lange das Gespräch noch dauert", async () => {
    renderPlayer();
    fireEvent.click(await loaded(10));
    act(() => FakeTrack.last!.at(4));
    const bar = screen.getByRole("progressbar", { name: "Fortschritt des Gesprächs" });
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(screen.getByText("noch 0:06")).toBeInTheDocument();
  });

  it("nennt vor dem Abspielen die ganze Dauer", async () => {
    renderPlayer();
    await loaded(23);
    expect(screen.getByText("noch 0:23")).toBeInTheDocument();
  });

  it("rechnet die Restzeit langsam mit", async () => {
    renderPlayer();
    fireEvent.click(await loaded(10));
    fireEvent.click(screen.getByRole("checkbox", { name: "langsam" }));
    act(() => FakeTrack.last!.at(4));
    expect(FakeTrack.last!.playbackRate).toBe(SLOW_PLAYBACK_RATE);
    expect(screen.getByText("noch 0:10")).toBeInTheDocument();
  });

  it("hält an und spielt an derselben Stelle weiter", async () => {
    renderPlayer();
    fireEvent.click(await loaded(10));
    act(() => FakeTrack.last!.at(3));
    fireEvent.click(screen.getByRole("button", { name: "⏸ Pause" }));
    expect(FakeTrack.last!.pause).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "▶ Weiter" }));
    expect(FakeTrack.last!.play).toHaveBeenCalledTimes(2);
    expect(FakeTrack.last!.currentTime).toBe(3);
  });

  it("hebt hervor, wer gerade spricht", async () => {
    renderPlayer();
    fireEvent.click(await loaded(10));
    act(() => FakeTrack.last!.at(3));
    // Zeile 2 beginnt bei 2,5 s — Nadja spricht.
    expect(screen.getByText("На́дя").closest("[aria-current]")).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(screen.getByText("Пётр").closest("span[aria-current]")).toBeNull();
  });

  it("meldet das Ende und bietet es noch einmal an", async () => {
    const onFinished = renderPlayer();
    fireEvent.click(await loaded(10));
    act(() => FakeTrack.last!.finish());
    expect(onFinished).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "▶ Nochmal" }));
    expect(FakeTrack.last!.currentTime).toBe(0);
  });

  it("hält die Spur an, wenn man die Seite verlässt", async () => {
    const { unmount } = render(
      <DialogPlayer dialogId={7} speakers={speakers} lines={lines} />,
    );
    fireEvent.click(await loaded(10));
    const spur = FakeTrack.last!;
    unmount();
    expect(spur.pause).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:gespraech");
  });
});

describe("DialogPlayer ohne Tonspur", () => {
  it("fällt auf Zeile für Zeile zurück, wenn die Spur nicht kommt", async () => {
    voice("server");
    vi.spyOn(api, "loadDialogTrack").mockRejectedValue(new Error("503"));
    renderPlayer();
    const button = await screen.findByRole("button", { name: /Abspielen/ });
    await act(async () => fireEvent.click(button));
    await waitFor(() => expect(say).toHaveBeenCalledTimes(3));
    expect(say.mock.calls.map((call) => call[1].voice)).toEqual(["m", "f", "m"]);
  });

  it("wartet mit jeder Zeile, bis die vorige gesprochen ist", async () => {
    // Der gemeldete Fehler: jede Zeile brach die vorige ab, zu hören war nur die letzte.
    voice("browser");
    const loadTrack = vi.spyOn(api, "loadDialogTrack");
    const offen: (() => void)[] = [];
    say.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          offen.push(resolve);
        }),
    );
    renderPlayer();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Abspielen/ })));

    expect(loadTrack).not.toHaveBeenCalled();
    expect(say).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Zeile 1 von 3")).toBeInTheDocument();

    await act(async () => offen[0]());
    expect(say).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Zeile 2 von 3")).toBeInTheDocument();

    await act(async () => offen[1]());
    await act(async () => offen[2]());
    expect(say).toHaveBeenCalledTimes(3);
  });
});
