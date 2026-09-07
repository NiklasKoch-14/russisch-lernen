import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RussianText from "./RussianText";
import { TransliterationContext } from "./TransliterationContext";

const word = { text: "де́лаю", translit: "délaju" };

function renderText(show = true, props: { revealed?: boolean } = {}) {
  return render(
    <TransliterationContext.Provider value={{ show, setShow: vi.fn() }}>
      <RussianText word={word} {...props} />
    </TransliterationContext.Provider>,
  );
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("RussianText", () => {
  it("zeigt zuerst nur die Kyrilliza", () => {
    renderText();
    expect(screen.getByText("де́лаю")).toBeVisible();
    expect(screen.queryByText("délaju")).not.toBeVisible();
  });

  it("deckt die Aussprache nach einer Sekunde Hovern auf", () => {
    const { container } = renderText();
    fireEvent.mouseEnter(container.firstChild as Element);

    act(() => vi.advanceTimersByTime(999));
    expect(screen.queryByText("délaju")).not.toBeVisible();

    act(() => vi.advanceTimersByTime(1));
    expect(screen.getByText("délaju")).toBeVisible();
  });

  it("verbirgt sie wieder, wenn die Maus weggeht", () => {
    const { container } = renderText();
    const target = container.firstChild as Element;

    fireEvent.mouseEnter(target);
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByText("délaju")).toBeVisible();

    fireEvent.mouseLeave(target);
    expect(screen.queryByText("délaju")).not.toBeVisible();
  });

  it("deckt nichts auf, wenn die Maus vorher weggeht", () => {
    const { container } = renderText();
    const target = container.firstChild as Element;

    fireEvent.mouseEnter(target);
    act(() => vi.advanceTimersByTime(500));
    fireEvent.mouseLeave(target);
    act(() => vi.advanceTimersByTime(1000));

    expect(screen.queryByText("délaju")).not.toBeVisible();
  });

  it("hält den Platz frei, damit die Karte beim Aufdecken nicht springt", () => {
    // Der Text ist da, nur unsichtbar — sonst waechst die Karte um eine Zeile
    // und die ganze Zeile der Zuordnungsaufgabe verschiebt sich.
    renderText();
    expect(screen.getByText("délaju")).toBeInTheDocument();
  });

  it("zeigt gar keine Umschrift, wenn sie im Profil abgeschaltet ist", () => {
    const { container } = renderText(false);
    fireEvent.mouseEnter(container.firstChild as Element);
    act(() => vi.advanceTimersByTime(2000));
    expect(screen.queryByText("délaju")).toBeNull();
  });

  it("folgt dem Elternteil, wenn dieser das Aufdecken steuert", () => {
    const { rerender } = renderText(true, { revealed: false });
    expect(screen.queryByText("délaju")).not.toBeVisible();

    rerender(
      <TransliterationContext.Provider value={{ show: true, setShow: vi.fn() }}>
        <RussianText word={word} revealed />
      </TransliterationContext.Provider>,
    );
    expect(screen.getByText("délaju")).toBeVisible();
  });
});
