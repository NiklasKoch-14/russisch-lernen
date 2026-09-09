import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import TypeSentenceExercise from "./TypeSentenceExercise";

const exercise = {
  id: "bar-01:s1#0",
  type: "type_sentence" as const,
  prompt_de: "Sag, dass es dir gut geht.",
  word_count: 3,
};

const renderExercise = (props = {}) =>
  render(<TypeSentenceExercise exercise={exercise} onSubmit={vi.fn()} {...props} />);

const field = () => screen.getByLabelText("Deine Antwort auf Russisch") as HTMLInputElement;

describe("TypeSentenceExercise", () => {
  it("zeigt den Auftrag und die Wortzahl", () => {
    renderExercise();
    expect(screen.getByText("Sag, dass es dir gut geht.")).toBeVisible();
    expect(screen.getByText("3 Wörter")).toBeVisible();
  });

  it("erinnert daran, den Satz erst zu sagen", () => {
    renderExercise();
    expect(screen.getByText("Erst laut sagen, dann tippen.")).toBeVisible();
  });

  it("schickt den getippten Satz", () => {
    const onSubmit = vi.fn();
    renderExercise({ onSubmit });
    fireEvent.change(field(), { target: { value: "хорошо а ты" } });
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(onSubmit).toHaveBeenCalledWith({ text: "хорошо а ты" });
  });

  it("prüft auch auf Enter", () => {
    const onSubmit = vi.fn();
    renderExercise({ onSubmit });
    fireEvent.change(field(), { target: { value: "пока" } });
    fireEvent.keyDown(field(), { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith({ text: "пока" });
  });

  it("prüft nicht ohne Eingabe", () => {
    renderExercise();
    expect(screen.getByRole("button", { name: "Prüfen" })).toBeDisabled();
  });

  it("prüft nicht bei blossem Leerraum", () => {
    renderExercise();
    fireEvent.change(field(), { target: { value: "   " } });
    expect(screen.getByRole("button", { name: "Prüfen" })).toBeDisabled();
  });

  it("schreibt Buchstaben von der Bildschirmtastatur ins Feld", () => {
    renderExercise();
    fireEvent.click(screen.getByRole("button", { name: "п" }));
    fireEvent.click(screen.getByRole("button", { name: "о" }));
    expect(field().value).toBe("по");
  });

  it("fügt an der Cursorposition ein, nicht am Ende", () => {
    // Sonst kann man einen vergessenen Buchstaben nur durch Neutippen nachtragen.
    renderExercise();
    fireEvent.change(field(), { target: { value: "чй" } });
    field().setSelectionRange(1, 1);
    fireEvent.click(screen.getByRole("button", { name: "а" }));
    expect(field().value).toBe("чай");
  });

  it("löscht das Zeichen vor dem Cursor", () => {
    renderExercise();
    fireEvent.change(field(), { target: { value: "чайx" } });
    field().setSelectionRange(4, 4);
    fireEvent.click(screen.getByRole("button", { name: "Löschen" }));
    expect(field().value).toBe("чай");
  });
});

describe("TypeSentenceExercise — nach dem Prüfen", () => {
  const answered = (props = {}) => {
    const view = renderExercise(props);
    fireEvent.change(field(), { target: { value: "я на работа" } });
    view.rerender(
      <TypeSentenceExercise
        exercise={exercise}
        onSubmit={vi.fn()}
        disabled
        {...props}
      />,
    );
    return view;
  };

  it("zeigt die eigene Antwort wortweise", () => {
    answered({ wrongWordIndex: 2 });
    const shown = screen.getByTestId("typed-answer");
    expect(shown.textContent).toBe("янаработа");
  });

  it("färbt das beanstandete Wort rot und alles davor grün", () => {
    answered({ wrongWordIndex: 2 });
    const shown = screen.getByTestId("typed-answer");
    const marks = [...shown.querySelectorAll("span")].map((span) => span.className);
    expect(marks[0]).toContain("emerald");
    expect(marks[1]).toContain("emerald");
    expect(marks[2]).toContain("rose");
  });

  it("färbt eine richtige Antwort ganz grün", () => {
    answered({ wrongWordIndex: null });
    const marks = [...screen.getByTestId("typed-answer").querySelectorAll("span")];
    expect(marks.every((span) => span.className.includes("emerald"))).toBe(true);
  });

  it("sperrt die Tastatur", () => {
    answered({ wrongWordIndex: 1 });
    expect(screen.getByRole("button", { name: "й" })).toBeDisabled();
  });
});
