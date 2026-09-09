import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { rectStyle } from "../game/rect";
import { artUrl, getVillage } from "../gameApi";
import type { Place } from "../gameTypes";

export default function VillageView() {
  const navigate = useNavigate();
  const [places, setPlaces] = useState<Place[] | null>(null);
  const [error, setError] = useState(false);
  const [mapMissing, setMapMissing] = useState(false);

  useEffect(() => {
    getVillage()
      .then((village) => setPlaces(village.places))
      .catch(() => setError(true));
  }, []);

  if (error) return <p>Das Dorf konnte nicht geladen werden.</p>;
  if (!places) return <p>Das Dorf wird geladen …</p>;

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Дере́вня — dein Dorf</h2>
      {/* Die Karte gibt das Seitenverhaeltnis vor; die Klickflaechen sind
          Anteile davon und sitzen deshalb bei jeder Fenstergroesse richtig.
          Fehlt das Bild, traegt der Kasten selbst das Verhaeltnis und die
          Flaechen bekommen sichtbare Beschriftung — das Dorf bleibt begehbar. */}
      <div
        data-testid="village-map"
        className={`relative mx-auto aspect-[16/9] w-full max-w-[1600px] overflow-hidden rounded-2xl ${
          mapMissing ? "bg-slate-200" : ""
        }`}
      >
        {!mapMissing && (
          <img
            src={artUrl("village")}
            alt="Das Dorf"
            onError={() => setMapMissing(true)}
            className="block h-full w-full object-cover"
          />
        )}
        {places.map((place) => (
          <button
            key={place.id}
            type="button"
            onClick={() => navigate(`/dorf/${place.id}`)}
            title={place.name_de}
            style={rectStyle(place.hotspot)}
            className="absolute flex items-center justify-center rounded-xl border-2 border-transparent transition hover:border-sky-500 hover:bg-sky-500/10 focus:border-sky-600 focus:outline-none"
          >
            {mapMissing ? (
              <span className="rounded-lg bg-white/90 px-2 py-1 text-sm font-medium">
                {place.name_ru}
              </span>
            ) : (
              <span className="sr-only">
                {place.name_ru} — {place.name_de}
              </span>
            )}
          </button>
        ))}
      </div>
      {/* Nur als Rueckfall: solange die Karte da ist, tragen die Gebaeude
          ihre Schilder im Bild — die Liste waere dieselbe Angabe ein zweites
          Mal. Fehlt das Bild, ist sie der einzige Weg zu den Namen. */}
      {mapMissing && (
      <ul className="flex flex-wrap gap-3 text-sm text-slate-600">
        {places.map((place) => (
          <li key={place.id}>
            <span className="font-medium text-slate-900">{place.name_ru}</span> {place.name_de}
          </li>
        ))}
      </ul>
      )}
    </section>
  );
}
