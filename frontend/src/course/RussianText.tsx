import type { Word } from "../courseTypes";
import { useTransliteration } from "./TransliterationContext";
import { useRevealOnHover } from "./useRevealOnHover";

export default function RussianText({
  word,
  className = "",
  revealed,
}: {
  word: Word;
  className?: string;
  /** Von aussen gesteuert — die Karte uebernimmt das Aufdecken selbst. */
  revealed?: boolean;
}) {
  const { show } = useTransliteration();
  const own = useRevealOnHover();
  const controlled = revealed !== undefined;
  const visible = controlled ? revealed : own.revealed;

  return (
    <span
      className={`inline-flex flex-col items-center leading-tight ${className}`}
      {...(controlled ? {} : own.bind)}
    >
      <span lang="ru">{word.text}</span>
      {show && word.translit ? (
        // Immer im Baum, nur unsichtbar: sonst waechst das Element beim
        // Aufdecken um eine Zeile und die ganze Zeile verschiebt sich.
        <span
          aria-hidden={!visible}
          // Sichtbarkeit als echter Stil, nicht als Klasse: so ist sie
          // unabhaengig vom Stylesheet und in Tests wirklich pruefbar.
          style={{ visibility: visible ? "visible" : "hidden" }}
          className={`text-xs text-slate-500 transition-opacity ${
            visible ? "opacity-100" : "opacity-0"
          }`}
        >
          {word.translit}
        </span>
      ) : null}
    </span>
  );
}
