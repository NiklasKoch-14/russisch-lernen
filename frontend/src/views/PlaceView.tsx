import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import PlaceHeader from "../game/PlaceHeader";
import PlaceStage from "../game/PlaceStage";
import { artUrl, getPlace, startScene } from "../gameApi";
import type { PlaceDetail } from "../gameTypes";

const ACTION = "rounded-xl bg-sky-600 px-5 py-2 font-medium text-white disabled:bg-slate-300";
const BACK = "rounded-xl border-2 border-slate-300 px-5 py-2 font-medium text-slate-700 hover:border-sky-400";

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
    <section className="mx-auto max-w-5xl space-y-6">
      <PlaceHeader nameRu={place.name_ru} nameDe={place.name_de} />

      {artMissing ? (
        <img
          src={artUrl(place.art)}
          alt={place.name_de}
          className="block w-full rounded-2xl"
        />
      ) : (
        // Auch Orte ohne Personen benutzen die Bühne: gleicher Zuschnitt,
        // gleicher Rückfall, kein zweiter Weg, ein Bild zu zeigen.
        <PlaceStage
          art={place.art}
          altText={place.name_de}
          npcs={place.npcs}
          onSelect={selectable ? (npc) => open(npc.id) : undefined}
          onArtMissing={() => setArtMissing(true)}
        />
      )}

      {place.kind === "npcs" && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {place.npcs
            .filter((npc) => artMissing || npc.spot == null)
            .map((npc) => (
              <li key={npc.id}>
                <button
                  type="button"
                  onClick={() => open(npc.id)}
                  className="flex w-full items-center gap-3 rounded-2xl border-2 border-slate-200 p-3 text-left hover:border-sky-400"
                >
                  <img src={artUrl(npc.art)} alt="" className="h-16 w-16 rounded-full object-contain" />
                  <span>
                    <span className="block font-medium">{npc.name_ru}</span>
                    <span className="block text-sm text-slate-600">{npc.about_de}</span>
                  </span>
                </button>
              </li>
            ))}
        </ul>
      )}

      <div data-testid="place-actions" className="flex flex-wrap items-center gap-3">
        {place.kind === "course" && (
          <button
            type="button"
            disabled={!place.next_unit_id}
            onClick={() => place.next_unit_id && navigate(`/kurs/${place.next_unit_id}`)}
            className={ACTION}
          >
            {place.next_unit_id ? `Einheit ${place.next_unit_id} beginnen` : "Alles geschafft"}
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
    </section>
  );
}
