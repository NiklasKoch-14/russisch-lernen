import { useState, type ReactNode } from "react";

import { artUrl } from "../gameApi";
import { rectStyle } from "./rect";
import type { Npc } from "../gameTypes";

interface Props {
  /** Bild-Id des Raums. */
  art: string;
  altText: string;
  npcs: Npc[];
  /** Fehlt der Rückruf, ist niemand anklickbar — so während eines Gesprächs. */
  onSelect?: (npc: Npc) => void;
  /** Wer gerade angesprochen wird: alle anderen treten zurück. */
  focusNpcId?: string | null;
  /** Wird gemeldet, wenn es zum Raum kein Bild gibt; der Aufrufer weicht dann aus. */
  onArtMissing?: () => void;
  /** Liegt über dem Raum — die Dialogkarte. */
  children?: ReactNode;
  /** Größenklassen von außen. Das Seitenverhältnis bleibt in jedem Fall: die
      Figuren sitzen auf Anteilen davon. */
  className?: string;
}

/**
 * Ein Raum mit den Leuten darin.
 *
 * Die Figuren liegen als eigene Ebene über dem Raumbild, positioniert aus den
 * Anteilen in `spot` — dasselbe Verfahren, mit dem `VillageView` die Gebäude
 * auf die Karte legt. Wer kein `spot` hat, steht in keinem Raum und wird hier
 * übergangen; die Ortsansicht führt solche Leute unter dem Bild auf.
 */
export default function PlaceStage({
  art,
  altText,
  npcs,
  onSelect,
  focusNpcId,
  onArtMissing,
  children,
  className = "w-full",
}: Props) {
  const [artMissing, setArtMissing] = useState(false);
  // Lose Prüfung mit Absicht: fehlt das Feld ganz (ältere Nutzlast, Testdaten),
  // ist es undefined und nicht null — beides heißt: steht in keinem Raum.
  const standing = npcs.filter((npc) => npc.spot != null);

  return (
    <div
      data-testid="place-stage"
      className={`relative aspect-[3/2] overflow-hidden ${className} ${
        artMissing ? "bg-slate-200" : ""
      }`}
    >
      {!artMissing && (
        <img
          src={artUrl(art)}
          alt={altText}
          onError={() => {
            setArtMissing(true);
            onArtMissing?.();
          }}
          className="block h-full w-full object-cover"
        />
      )}

      {standing.map((npc) => (
        <Figure
          key={npc.id}
          npc={npc}
          onSelect={onSelect}
          dimmed={focusNpcId != null && focusNpcId !== npc.id}
        />
      ))}

      {children}
    </div>
  );
}



function Figure({
  npc,
  onSelect,
  dimmed,
}: {
  npc: Npc;
  onSelect?: (npc: Npc) => void;
  dimmed: boolean;
}) {
  const [drawingMissing, setDrawingMissing] = useState(false);
  const position = rectStyle(npc.spot!);

  const body = drawingMissing ? (
    // Ohne Zeichnung bleibt der Name stehen: die Person ist weiter zu finden
    // und, wo es Gespräche gibt, weiter anzusprechen.
    <span className="rounded-lg bg-white/90 px-2 py-1 text-sm font-medium">{npc.name_ru}</span>
  ) : (
    <img
      src={artUrl(npc.art)}
      alt={npc.name_ru}
      onError={() => setDrawingMissing(true)}
      // Unten ausgerichtet, damit die Füße auf dem Boden stehen und nicht
      // mittig im Rechteck schweben.
      className="h-full w-full object-contain object-bottom"
    />
  );

  const shared = "absolute flex items-end justify-center transition";
  const shade = dimmed ? "opacity-40 grayscale" : "";

  if (!onSelect) {
    return (
      <div
        data-testid={`figure-${npc.id}`}
        style={position}
        className={`${shared} ${shade}`}
      >
        {body}
      </div>
    );
  }

  return (
    <button
      type="button"
      data-testid={`figure-${npc.id}`}
      onClick={() => onSelect(npc)}
      title={`${npc.name_de} — ${npc.about_de}`}
      style={position}
      className={`${shared} ${shade} rounded-xl hover:bg-sky-400/20 focus:outline-none focus:ring-4 focus:ring-sky-500`}
    >
      {body}
      {/* Ohne Schild sieht man im Raum nur Gestalten und muss raten, wer wer
          ist. Fehlt die Zeichnung, steht der Name ohnehin schon da. */}
      {!drawingMissing && (
        <span className="pointer-events-none absolute bottom-0 rounded bg-white/85 px-1.5 py-0.5 text-xs font-medium text-slate-900">
          {npc.name_ru}
        </span>
      )}
      <span className="sr-only">{npc.about_de}</span>
    </button>
  );
}
