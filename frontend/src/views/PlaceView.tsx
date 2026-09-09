import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import PlaceHeader from "../game/PlaceHeader";
import PlaceStage from "../game/PlaceStage";
import { artUrl, getPlace, startScene } from "../gameApi";
import type { PlaceDetail } from "../gameTypes";

const ACTION =
  "rounded-xl bg-sky-600 px-5 py-2 font-medium text-white shadow disabled:bg-slate-300";
const BACK =
  "rounded-xl border-2 border-slate-300 bg-white/90 px-5 py-2 font-medium text-slate-700 shadow backdrop-blur-sm hover:border-sky-400";

export default function PlaceView() {
  const { placeId } = useParams();
  const navigate = useNavigate();
  const [place, setPlace] = useState<PlaceDetail | null>(null);
  const [error, setError] = useState(false);
  /** Ohne Raumbild gibt es keine Bühne — dann wieder die Liste wie früher. */
  const [artMissing, setArtMissing] = useState(false);

  useEffect(() => {
    if (!placeId) return;
    getPlace(placeId)
      .then(setPlace)
      .catch(() => setError(true));
  }, [placeId]);

  // "npcs" braucht die Wahl der Person, "shopping" nicht — deshalb startet
  // hier auch die Einkaufsszene ohne npcId.
  const open = (npcId?: string) => {
    if (!placeId) return;
    startScene(placeId, npcId)
      .then((scene) =>
        navigate(
          `/dorf/${placeId}/szene/${scene.scene_id}?seed=${encodeURIComponent(scene.seed)}`,
        ),
      )
      .catch(() => setError(true));
  };

  if (error) return <p>Der Ort konnte nicht geladen werden.</p>;
  if (!place) return <p>Ort wird geladen …</p>;

  /** Nur wo Personen im Raum stehen, ist die Bühne auch anklickbar. */
  const selectable = place.kind === "npcs" && !artMissing;

  return (
    <section className="flex w-full flex-col gap-4 sm:min-h-0 sm:flex-1">
      {artMissing ? (
        <>
          <PlaceHeader nameRu={place.name_ru} nameDe={place.name_de} />
          <img src={artUrl(place.art)} alt={place.name_de} className="block w-full rounded-2xl" />
        </>
      ) : (
        <div className="flex justify-center sm:min-h-0 sm:flex-1">
        <div className="relative mx-auto aspect-[3/2] w-full overflow-hidden rounded-2xl sm:h-full sm:w-auto sm:max-w-full">
          <PlaceStage
            art={place.art}
            altText={place.name_de}
            npcs={place.npcs}
            onSelect={selectable ? (npc) => open(npc.id) : undefined}
            onArtMissing={() => setArtMissing(true)}
            className="h-full w-full"
          />
          {/* Aufsätze liegen über dem Bild: der Raum soll den Platz ganz
              ausfüllen, Name und Wege schweben darauf. */}
          <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-4 sm:p-6">
            <div className="pointer-events-auto self-start pt-14 sm:pt-16">
              <PlaceHeader nameRu={place.name_ru} nameDe={place.name_de} onImage />
            </div>
            <div
              data-testid="place-actions"
              className="pointer-events-auto flex flex-wrap items-center gap-3 self-end"
            >
              {place.kind === "course" && (
                <button
                  type="button"
                  disabled={!place.next_unit_id}
                  onClick={() => place.next_unit_id && navigate(`/kurs/${place.next_unit_id}`)}
                  className={ACTION}
                >
                  {place.next_unit_id
                    ? `Einheit ${place.next_unit_id} beginnen`
                    : "Alles geschafft"}
                </button>
              )}
              {place.kind === "shopping" && (
                <button type="button" onClick={() => open(undefined)} className={ACTION}>
                  Einkaufen gehen
                </button>
              )}
              <button type="button" onClick={() => navigate("/dorf")} className={BACK}>
                Zurück ins Dorf
              </button>
            </div>
          </div>
        </div>
        </div>
      )}

      {place.kind === "npcs" && artMissing && (
        <>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {place.npcs.map((npc) => (
              <li key={npc.id}>
                <button
                  type="button"
                  onClick={() => open(npc.id)}
                  className="flex w-full items-center gap-3 rounded-2xl border-2 border-slate-200 p-3 text-left hover:border-sky-400"
                >
                  <img
                    src={artUrl(npc.art)}
                    alt=""
                    className="h-16 w-16 rounded-full object-contain"
                  />
                  <span>
                    <span className="block font-medium">{npc.name_ru}</span>
                    <span className="block text-sm text-slate-600">{npc.about_de}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <div data-testid="place-actions" className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={() => navigate("/dorf")} className={BACK}>
              Zurück ins Dorf
            </button>
          </div>
        </>
      )}

      {/* Leute ohne Platz im Raum bleiben über die Liste erreichbar. */}
      {place.kind === "npcs" && !artMissing && place.npcs.some((npc) => npc.spot == null) && (
        <ul className="flex flex-wrap gap-3">
          {place.npcs
            .filter((npc) => npc.spot == null)
            .map((npc) => (
              <li key={npc.id}>
                <button
                  type="button"
                  onClick={() => open(npc.id)}
                  className="rounded-xl border-2 border-slate-200 px-3 py-2 font-medium hover:border-sky-400"
                >
                  {npc.name_ru}
                </button>
              </li>
            ))}
        </ul>
      )}
    </section>
  );
}
