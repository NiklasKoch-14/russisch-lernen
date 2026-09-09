/**
 * Der Kopf einer Ortsseite: russischer Name groß, deutscher klein darunter.
 *
 * Liegt hier und nicht in den beiden Ansichten, damit das Ansprechen einer
 * Person nicht die halbe Seitengestalt wechselt — Raum und Gespräch tragen
 * denselben Kopf.
 */
export default function PlaceHeader({
  nameRu,
  nameDe,
  onImage = false,
}: {
  nameRu: string;
  nameDe: string;
  /** Auf dem Bild: weiß mit schwarzer Kontur, damit der Name über jedem
      Untergrund lesbar bleibt — hell wie dunkel. */
  onImage?: boolean;
}) {
  const outline = onImage
    ? "text-white [paint-order:stroke_fill] [-webkit-text-stroke:3px_#0f172a] drop-shadow"
    : "";
  const sub = onImage
    ? "text-white/90 [paint-order:stroke_fill] [-webkit-text-stroke:2px_#0f172a]"
    : "text-slate-600";

  return (
    <header data-testid="place-header" className="space-y-1">
      <h2 className={`font-semibold ${onImage ? "text-4xl" : "text-2xl"} ${outline}`}>
        {nameRu}
      </h2>
      <p className={`font-medium ${onImage ? "text-lg" : ""} ${sub}`}>{nameDe}</p>
    </header>
  );
}
