import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import NewWords from "./NewWords";

const words = [
  { id: "govorit", text: "говори́ть", translit: "govorít'", gloss_de: "sprechen" },
  { id: "ne", text: "не", translit: "ne", gloss_de: "nicht" },
];

describe("NewWords", () => {
  it("zeigt jedes neue Wort mit seiner Bedeutung", () => {
    render(<NewWords words={words} onContinue={vi.fn()} />);
    expect(screen.getByText("говори́ть")).toBeVisible();
    expect(screen.getByText("sprechen")).toBeVisible();
    expect(screen.getByText("не")).toBeVisible();
    expect(screen.getByText("nicht")).toBeVisible();
  });

  it("zeigt die Bedeutung sofort, nicht erst beim Hovern", () => {
    // Der Bildschirm soll erklaeren, nicht abfragen.
    render(<NewWords words={words} onContinue={vi.fn()} />);
    expect(screen.getByText("sprechen")).toBeVisible();
  });

  it("führt weiter zu den Aufgaben", () => {
    const onContinue = vi.fn();
    render(<NewWords words={words} onContinue={onContinue} />);
    fireEvent.click(screen.getByRole("button", { name: /Aufgaben/ }));
    expect(onContinue).toHaveBeenCalled();
  });

  it("nennt die Anzahl der neuen Wörter", () => {
    render(<NewWords words={words} onContinue={vi.fn()} />);
    expect(screen.getByText(/2 neue Wörter/)).toBeInTheDocument();
  });

  it("beugt sich dem Singular bei einem einzigen Wort", () => {
    render(<NewWords words={[words[0]]} onContinue={vi.fn()} />);
    expect(screen.getByText(/1 neues Wort/)).toBeInTheDocument();
  });
});
