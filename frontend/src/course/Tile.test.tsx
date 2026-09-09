import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Tile from "./Tile";

const word = { text: "де́лаю", translit: "délaju", gloss_de: "machen, tun" };

const renderTile = () =>
  render(<Tile word={word} state="idle" onClick={vi.fn()} />);

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("Tile", () => {
  it("zeigt den russischen Text", () => {
    renderTile();
    expect(screen.getByText("де́лаю")).toBeVisible();
  });

  it("meldet den Klick", () => {
    const onClick = vi.fn();
    render(<Tile word={word} state="idle" onClick={onClick} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalled();
  });

  it("lässt sich sperren", () => {
    render(<Tile word={word} state="idle" onClick={vi.fn()} disabled />);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});

describe("Tile — Aufdecken der Aussprache", () => {
  it("verbirgt die Aussprache zunächst", () => {
    renderTile();
    expect(screen.queryByText("délaju")).not.toBeVisible();
  });

  it("zeigt den Ladekreis nicht sofort", () => {
    // Beim blossen Vorbeifahren soll nichts aufblitzen.
    renderTile();
    fireEvent.mouseEnter(screen.getByRole("button"));
    expect(screen.queryByTestId("reveal-ring")).toBeNull();

    act(() => vi.advanceTimersByTime(332));
    expect(screen.queryByTestId("reveal-ring")).toBeNull();
  });

  it("zeigt den Ladekreis nach einem Drittel der Wartezeit", () => {
    renderTile();
    fireEvent.mouseEnter(screen.getByRole("button"));
    act(() => vi.advanceTimersByTime(334));
    expect(screen.getByTestId("reveal-ring")).toBeInTheDocument();
  });

  it("lässt den Ladekreis bei einem Drittel einsetzen, nicht bei null", () => {
    // Sonst liefe er dem Aufdecken hinterher und log ueber die Restzeit.
    renderTile();
    fireEvent.mouseEnter(screen.getByRole("button"));
    act(() => vi.advanceTimersByTime(334));

    const ring = screen.getByTestId("reveal-ring").querySelector("[style]") as HTMLElement;
    expect(ring.style.animation).toContain("-333");
  });

  it("nimmt den Ladekreis weg, sobald aufgedeckt ist", () => {
    // Bei einem Wort ohne Bedeutung ist mit der Aussprache Schluss; wo es eine
    // gibt, dreht der Kreis eine zweite Runde (siehe unten).
    render(
      <Tile word={{ text: "де́лаю", translit: "délaju" }} state="idle" onClick={vi.fn()} />,
    );
    fireEvent.mouseEnter(screen.getByRole("button"));
    act(() => vi.advanceTimersByTime(1000));

    expect(screen.getByText("délaju")).toBeVisible();
    expect(screen.queryByTestId("reveal-ring")).toBeNull();
  });

  it("nimmt den Ladekreis weg, wenn die Maus vorher weggeht", () => {
    renderTile();
    const button = screen.getByRole("button");
    fireEvent.mouseEnter(button);
    act(() => vi.advanceTimersByTime(400));
    expect(screen.getByTestId("reveal-ring")).toBeInTheDocument();
    fireEvent.mouseLeave(button);

    expect(screen.queryByTestId("reveal-ring")).toBeNull();
    expect(screen.queryByText("délaju")).not.toBeVisible();
  });

  it("zeigt ohne Umschrift auch keinen Ladekreis", () => {
    render(<Tile word={{ text: "и", translit: "" }} state="idle" onClick={vi.fn()} />);
    fireEvent.mouseEnter(screen.getByRole("button"));
    act(() => vi.advanceTimersByTime(500));
    expect(screen.queryByTestId("reveal-ring")).toBeNull();
  });
});


describe("Tile — Aufdecken der Bedeutung", () => {
  it("zeigt die Bedeutung erst nach 2,5 Sekunden", () => {
    renderTile();
    fireEvent.mouseEnter(screen.getByRole("button"));

    act(() => vi.advanceTimersByTime(1000));
    // Erst die Aussprache — die Bedeutung nimmt sonst das Nachdenken vorweg.
    expect(screen.getByText("délaju")).toBeVisible();
    expect(screen.queryByText("machen, tun")).toBeNull();

    act(() => vi.advanceTimersByTime(1500));
    expect(screen.getByText("machen, tun")).toBeVisible();
  });

  it("laesst den Ladekreis eine zweite Runde drehen", () => {
    renderTile();
    fireEvent.mouseEnter(screen.getByRole("button"));

    act(() => vi.advanceTimersByTime(1000));
    const ring = screen.getByTestId("reveal-ring").querySelector("[style]") as HTMLElement;
    // Zweite Runde: volle 1500 ms, ohne den Startversatz der ersten.
    expect(ring.style.animation).toContain("1500ms");
  });

  it("dreht keine zweite Runde ohne Bedeutung", () => {
    render(
      <Tile word={{ text: "де́лаю", translit: "délaju" }} state="idle" onClick={vi.fn()} />,
    );
    fireEvent.mouseEnter(screen.getByRole("button"));
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.queryByTestId("reveal-ring")).toBeNull();
  });

  it("hoert nach der zweiten Runde auf zu drehen", () => {
    renderTile();
    fireEvent.mouseEnter(screen.getByRole("button"));
    act(() => vi.advanceTimersByTime(2500));
    expect(screen.queryByTestId("reveal-ring")).toBeNull();
  });

  it("nimmt die Bedeutung weg, wenn die Maus weggeht", () => {
    renderTile();
    const button = screen.getByRole("button");
    fireEvent.mouseEnter(button);
    act(() => vi.advanceTimersByTime(2500));
    expect(screen.getByText("machen, tun")).toBeVisible();

    fireEvent.mouseLeave(button);
    expect(screen.queryByText("machen, tun")).toBeNull();
  });
});
