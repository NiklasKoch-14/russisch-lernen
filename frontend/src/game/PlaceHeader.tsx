/**
 * Der Kopf einer Ortsseite: russischer Name groß, deutscher klein darunter.
 *
 * Liegt hier und nicht in den beiden Ansichten, damit das Ansprechen einer
 * Person nicht die halbe Seitengestalt wechselt — Raum und Gespräch tragen
 * denselben Kopf.
 */
export default function PlaceHeader({ nameRu, nameDe }: { nameRu: string; nameDe: string }) {
  return (
    <header data-testid="place-header" className="space-y-1">
      <h2 className="text-2xl font-semibold">{nameRu}</h2>
      <p className="text-slate-600">{nameDe}</p>
    </header>
  );
}
