import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Npc } from "../gameTypes";
import PlaceStage from "./PlaceStage";

const pjotr: Npc = {
  id: "pjotr",
  name_ru: "Пётр",
  name_de: "Pjotr",
  about_de: "Sitzt jeden Abend am selben Platz.",
  art: "npc_pjotr",
  spot: { x: 0.03, y: 0.36, w: 0.14, h: 0.42 },
};

const nadja: Npc = {
  id: "nadja",
  name_ru: "На́дя",
  name_de: "Nadja",
  about_de: "Steht hinter der Theke.",
  art: "npc_nadja",
  spot: { x: 0.8, y: 0.25, w: 0.13, h: 0.29 },
};

describe("PlaceStage", () => {
  it("setzt jede Figur auf die Anteile aus dem Inhalt", () => {
    render(<PlaceStage art="bar" altText="Bar" npcs={[pjotr]} onSelect={() => {}} />);
    const figure = screen.getByRole("button", { name: /Пётр/ });
    // Prozentwerte aus dem Inhalt, nicht aus dem Layout: sonst stünde die
    // Figur irgendwo im Raum statt an ihrem Platz.
    expect(figure.style.left).toBe("3%");
    expect(figure.style.top).toBe("36%");
    expect(figure.style.width).toBe("14%");
    expect(figure.style.height).toBe("42%");
  });

  it("meldet, wen man angeklickt hat", () => {
    const onSelect = vi.fn();
    render(<PlaceStage art="bar" altText="Bar" npcs={[pjotr, nadja]} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: /На́дя/ }));
    expect(onSelect).toHaveBeenCalledWith(nadja);
  });

  it("macht ohne onSelect niemanden anklickbar", () => {
    // Im laufenden Gespräch darf man die Person nicht wechseln.
    render(<PlaceStage art="bar" altText="Bar" npcs={[pjotr, nadja]} focusNpcId="pjotr" />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByAltText("Пётр")).toBeInTheDocument();
  });

  it("dunkelt alle ausser der angesprochenen Person ab", () => {
    render(<PlaceStage art="bar" altText="Bar" npcs={[pjotr, nadja]} focusNpcId="pjotr" />);
    const dimmed = screen.getByTestId("figure-nadja");
    const focused = screen.getByTestId("figure-pjotr");
    expect(dimmed.className).toMatch(/opacity-/);
    expect(focused.className).not.toMatch(/opacity-/);
  });

  it("schreibt den Namen unter jede anklickbare Figur", () => {
    // Im Raum sieht man sonst nur Gestalten und muss raten, wer wer ist.
    render(<PlaceStage art="bar" altText="Bar" npcs={[pjotr, nadja]} onSelect={() => {}} />);
    const label = within(screen.getByTestId("figure-nadja")).getByText("На́дя");
    expect(label).toBeVisible();
    expect(label).not.toHaveClass("sr-only");
  });

  it("laesst die Namensschilder im Gespraech weg", () => {
    // Wer gerade spricht, steht in der Dialogkarte; Schilder im Raum wuerden
    // waehrenddessen nur ablenken.
    render(<PlaceStage art="bar" altText="Bar" npcs={[pjotr, nadja]} focusNpcId="pjotr" />);
    expect(within(screen.getByTestId("figure-nadja")).queryByText("На́дя")).toBeNull();
  });

  it("laesst den Namen lesbar, wenn die Zeichnung fehlt", () => {
    render(<PlaceStage art="bar" altText="Bar" npcs={[pjotr]} onSelect={() => {}} />);
    fireEvent.error(screen.getByAltText("Пётр"));
    const figure = screen.getByRole("button", { name: /Пётр/ });
    const label = within(figure).getByText("Пётр");
    expect(label).toBeVisible();
    expect(label).not.toHaveClass("sr-only");
  });

  it("meldet dem Aufrufer, wenn das Raumbild fehlt", () => {
    const onArtMissing = vi.fn();
    render(
      <PlaceStage
        art="bar"
        altText="Bar"
        npcs={[pjotr]}
        onSelect={() => {}}
        onArtMissing={onArtMissing}
      />,
    );
    fireEvent.error(screen.getByAltText("Bar"));
    expect(onArtMissing).toHaveBeenCalled();
  });
});
