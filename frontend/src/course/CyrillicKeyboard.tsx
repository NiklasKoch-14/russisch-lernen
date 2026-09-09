/**
 * Kyrillische Bildschirmtastatur im Layout ЙЦУКЕН.
 *
 * Das echte russische Layout, nicht nach dem Alphabet sortiert: wer hier tippt,
 * findet die Tasten später auf jeder russischen Tastatur wieder.
 *
 * Betonungszeichen fehlen mit Absicht — sie werden beim Prüfen ohnehin
 * weggelassen, und ё gibt es aus demselben Grund nicht.
 */
const ROWS = ["йцукенгшщзхъ", "фывапролджэ", "ячсмитьбю"];

const KEY =
  "min-w-9 rounded-lg border border-slate-300 bg-white px-2 py-2 text-lg leading-none hover:border-sky-400 disabled:opacity-40";

export default function CyrillicKeyboard({
  onKey,
  onBackspace,
  disabled = false,
}: {
  onKey: (letter: string) => void;
  onBackspace: () => void;
  disabled?: boolean;
}) {
  return (
    <div data-testid="cyrillic-keyboard" className="space-y-1">
      {ROWS.map((row) => (
        <div key={row} className="flex justify-center gap-1">
          {[...row].map((letter) => (
            <button
              key={letter}
              type="button"
              tabIndex={-1}
              disabled={disabled}
              onClick={() => onKey(letter)}
              className={KEY}
            >
              {letter}
            </button>
          ))}
        </div>
      ))}
      <div className="flex justify-center gap-1">
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          onClick={() => onKey(" ")}
          className={`${KEY} w-40`}
        >
          Leerzeichen
        </button>
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          aria-label="Löschen"
          onClick={onBackspace}
          className={KEY}
        >
          ⌫
        </button>
      </div>
    </div>
  );
}
