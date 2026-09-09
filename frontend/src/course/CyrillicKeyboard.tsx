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

/**
 * Alle Tasten sind gleich breit, abgeleitet von der laengsten Reihe: zwoelf
 * Tasten plus elf Abstaende von 0,25rem. Feste Mindestbreiten liessen die
 * oberen Reihen aus der Dialogkarte laufen, sobald das Fenster kleiner wird.
 */
const KEY =
  "w-[calc((100%-2.75rem)/12)] rounded-lg border border-slate-300 bg-white py-2 text-lg leading-none hover:border-sky-400 disabled:opacity-40";

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
          className={`${KEY} !w-2/5`}
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
