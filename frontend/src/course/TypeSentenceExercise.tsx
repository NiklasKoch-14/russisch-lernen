import { useEffect, useRef, useState } from "react";

import type { TypeSentenceExercise as Model, Submission } from "../courseTypes";
import CyrillicKeyboard from "./CyrillicKeyboard";

/** Wortweise Einfärbung nach dem Prüfen: vor dem Fehler stimmte alles. */
function wordClass(position: number, wrongWordIndex: number | null | undefined): string {
  if (wrongWordIndex == null) return "bg-emerald-100";
  if (position < wrongWordIndex) return "bg-emerald-100";
  if (position === wrongWordIndex) return "bg-rose-200 font-semibold";
  return "bg-slate-100";
}

export default function TypeSentenceExercise({
  exercise,
  disabled = false,
  wrongWordIndex = null,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  /** Welches Wort beanstandet wurde — erst nach dem Prüfen gesetzt. */
  wrongWordIndex?: number | null;
  onSubmit: (submission: Submission) => void;
}) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  /** Wohin der Cursor nach einem Tastenklick gehört. */
  const caret = useRef<number | null>(null);

  useEffect(() => {
    if (caret.current === null) return;
    inputRef.current?.setSelectionRange(caret.current, caret.current);
    caret.current = null;
  }, [text]);

  // Maus und Tastatur sollen sich mischen lassen: eingefügt wird deshalb an der
  // Cursorposition, nicht am Ende, und der Fokus bleibt im Feld.
  const replaceSelection = (chunk: string, deleteBefore = false) => {
    const input = inputRef.current;
    const end = input?.selectionEnd ?? text.length;
    let start = input?.selectionStart ?? end;
    if (deleteBefore && start === end) start = Math.max(0, start - 1);
    setText(text.slice(0, start) + chunk + text.slice(end));
    caret.current = start + chunk.length;
    input?.focus();
  };

  const submit = () => {
    if (!disabled && text.trim() !== "") onSubmit({ text });
  };

  return (
    <div className="space-y-3">
      <p className="text-lg">{exercise.prompt_de}</p>
      {/* Kostet nichts und macht aus der Schreibübung eine Sprechübung. */}
      <p className="text-sm text-slate-500">Erst laut sagen, dann tippen.</p>

      {disabled ? (
        <p data-testid="typed-answer" className="flex flex-wrap gap-1 text-lg">
          {text.trim() === "" ? (
            <span className="text-slate-400">(nichts geschrieben)</span>
          ) : (
            text
              .trim()
              .split(/\s+/)
              .map((word, position) => (
                <span
                  key={`${word}-${position}`}
                  className={`rounded px-1 ${wordClass(position, wrongWordIndex)}`}
                >
                  {word}
                </span>
              ))
          )}
        </p>
      ) : (
        <input
          ref={inputRef}
          type="text"
          value={text}
          lang="ru"
          autoComplete="off"
          aria-label="Deine Antwort auf Russisch"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && submit()}
          className="w-full rounded-xl border-2 border-slate-300 px-3 py-2 text-lg focus:border-sky-400 focus:outline-none"
        />
      )}

      <p className="text-sm text-slate-500">
        {exercise.word_count === 1 ? "ein Wort" : `${exercise.word_count} Wörter`}
      </p>

      {/* Ueber der Tastatur: auf einem kleinen Fenster scrollt die Karte, und
          dann rutschte der Knopf als Erstes aus dem Blick. */}
      <button
        type="button"
        disabled={disabled || text.trim() === ""}
        onClick={submit}
        className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white disabled:opacity-50"
      >
        Prüfen
      </button>

      <CyrillicKeyboard
        disabled={disabled}
        onKey={(letter) => replaceSelection(letter)}
        onBackspace={() => replaceSelection("", true)}
      />
    </div>
  );
}
