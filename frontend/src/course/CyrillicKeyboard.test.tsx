import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CyrillicKeyboard from "./CyrillicKeyboard";

const renderKeyboard = (props = {}) =>
  render(<CyrillicKeyboard onKey={vi.fn()} onBackspace={vi.fn()} {...props} />);

describe("CyrillicKeyboard", () => {
  it("zeigt das russische Layout, nicht das Alphabet", () => {
    renderKeyboard();
    const letters = screen
      .getAllByRole("button")
      .map((button) => button.textContent)
      .filter((text) => text != null && /^[а-я]$/.test(text));
    expect(letters.slice(0, 3)).toEqual(["й", "ц", "у"]);
    expect(letters).toHaveLength(32);
  });

  it("meldet den angeklickten Buchstaben", () => {
    const onKey = vi.fn();
    renderKeyboard({ onKey });
    fireEvent.click(screen.getByRole("button", { name: "ж" }));
    expect(onKey).toHaveBeenCalledWith("ж");
  });

  it("hat eine Leertaste", () => {
    const onKey = vi.fn();
    renderKeyboard({ onKey });
    fireEvent.click(screen.getByRole("button", { name: "Leerzeichen" }));
    expect(onKey).toHaveBeenCalledWith(" ");
  });

  it("meldet das Löschen getrennt", () => {
    const onBackspace = vi.fn();
    renderKeyboard({ onBackspace });
    fireEvent.click(screen.getByRole("button", { name: "Löschen" }));
    expect(onBackspace).toHaveBeenCalled();
  });

  it("bleibt beim Tabben aussen vor", () => {
    // Sonst laeuft man sich beim Weiterspringen durch 32 Tasten.
    renderKeyboard();
    expect(screen.getByRole("button", { name: "й" })).toHaveAttribute("tabindex", "-1");
  });

  it("laesst sich sperren", () => {
    renderKeyboard({ disabled: true });
    expect(screen.getByRole("button", { name: "й" })).toBeDisabled();
  });
});
