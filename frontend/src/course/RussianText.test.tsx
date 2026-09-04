import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RussianText from "./RussianText";
import { TransliterationContext } from "./TransliterationContext";

const word = { text: "приве́т", translit: "privét" };

function renderWith(show: boolean) {
  return render(
    <TransliterationContext.Provider value={{ show, setShow: () => {} }}>
      <RussianText word={word} />
    </TransliterationContext.Provider>,
  );
}

describe("RussianText", () => {
  it("zeigt immer den kyrillischen Text", () => {
    renderWith(false);
    expect(screen.getByText("приве́т")).toBeInTheDocument();
  });

  it("zeigt die Umschrift, wenn sie eingeschaltet ist", () => {
    renderWith(true);
    expect(screen.getByText("privét")).toBeInTheDocument();
  });

  it("blendet die Umschrift aus, wenn sie abgeschaltet ist", () => {
    renderWith(false);
    expect(screen.queryByText("privét")).not.toBeInTheDocument();
  });
});
