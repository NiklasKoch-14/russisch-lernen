import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Tile from "./Tile";

const word = { text: "я", translit: "ja" };

describe("Tile", () => {
  it("meldet einen Klick", () => {
    const onClick = vi.fn();
    render(<Tile word={word} state="idle" onClick={onClick} />);
    fireEvent.click(screen.getByRole("button", { name: /я/ }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("meldet keinen Klick, wenn sie deaktiviert ist", () => {
    const onClick = vi.fn();
    render(<Tile word={word} state="idle" onClick={onClick} disabled />);
    fireEvent.click(screen.getByRole("button", { name: /я/ }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("markiert den Zustand für Hilfstechnologien", () => {
    render(<Tile word={word} state="selected" onClick={() => {}} />);
    expect(screen.getByRole("button", { name: /я/ })).toHaveAttribute("aria-pressed", "true");
  });
});
