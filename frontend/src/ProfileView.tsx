import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getLearningPlan } from "./api";
import { useSpeech } from "./audio/SpeechContext";
import { useTransliteration } from "./course/TransliterationContext";
import { getCourse, getProfile } from "./courseApi";
import type { CourseOverview, Profile } from "./courseTypes";

const CHAT_UNLOCK_STAGE = 3;

function chatUnlocked(overview: CourseOverview | null): boolean {
  if (!overview) return false;
  return overview.stages.some(
    (stage) =>
      stage.stage >= CHAT_UNLOCK_STAGE &&
      stage.units.some((unit) => unit.status === "completed"),
  );
}

export default function ProfileView() {
  const { show, setShow } = useTransliteration();
  const { available, lastError, activeVoice, source } = useSpeech();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [topics, setTopics] = useState<string[]>([]);
  const [overview, setOverview] = useState<CourseOverview | null>(null);

  useEffect(() => {
    getProfile().then(setProfile).catch(() => setProfile(null));
    getLearningPlan()
      .then((plan) => setTopics(plan?.topics ?? []))
      .catch(() => setTopics([]));
    getCourse().then(setOverview).catch(() => setOverview(null));
  }, []);

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <p>Aktuelles Level: {profile?.cefr_level ?? "wird ermittelt..."}</p>
        {profile?.placement_unit ? (
          <p className="text-slate-600">Empfohlener Einstieg: Einheit {profile.placement_unit}</p>
        ) : null}
        <Link to="/einstufung" className="inline-block text-sky-700 underline">
          Einstufung starten
        </Link>
      </section>

      <section>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={show}
            onChange={(event) => setShow(event.target.checked)}
          />
          Umschrift anzeigen
        </label>
      </section>

      {activeVoice ? (
        <section>
          <h2 className="text-lg font-semibold">Sprachausgabe</h2>
          <p className="text-slate-600">
            Aktive Stimme: <b>{activeVoice.name}</b> ({activeVoice.lang}) —{" "}
            {source === "server" ? (
              <span>eigener Sprachdienst im Stack, kein Umweg über fremde Server</span>
            ) : activeVoice.local ? (
              <span>Stimme deines Browsers, lokal installiert</span>
            ) : (
              <span>Stimme deines Browsers, online — klingt besser, setzt verzögert ein</span>
            )}
          </p>
        </section>
      ) : null}

      {lastError ? (
        <section className="rounded-2xl border-2 border-rose-200 bg-rose-50 p-4">
          <h2 className="text-lg font-semibold">Die Sprachausgabe hat gemeldet: {lastError}</h2>
          <p className="mt-1">
            Bei <code className="mx-1">network</code> oder{" "}
            <code className="mx-1">synthesis-failed</code> liegt es an der Online-Stimme, die
            Speaker bevorzugt — sie klingt besser als die lokalen Windows-Stimmen, braucht dafür
            aber eine Internetverbindung.
          </p>
        </section>
      ) : null}

      {available === false ? (
        <section className="rounded-2xl border-2 border-amber-200 bg-amber-50 p-4">
          <h2 className="text-lg font-semibold">Kein Ton</h2>
          <p className="mt-1">
            Dein Browser findet keine russische Stimme. Hör-Aufgaben werden deshalb als
            Textaufgaben angezeigt — du verlierst dadurch keine Übung. Unter Windows
            installierst du eine Stimme über Einstellungen → Zeit und Sprache → Sprache,
            unter Linux über <code className="mx-1">speech-dispatcher</code> mit russischer
            Stimme.
          </p>
        </section>
      ) : null}

      <section>
        <h2 className="text-lg font-semibold">Freies Gespräch</h2>
        {chatUnlocked(overview) ? (
          <Link to="/gespraech" className="text-sky-700 underline">
            Freies Gespräch öffnen
          </Link>
        ) : (
          <p className="text-slate-600">
            Freies Gespräch schaltet sich frei, sobald du Stufe 3 erreichst.
          </p>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold">Aktueller Lernplan</h2>
        {topics.length === 0 ? (
          <p>Noch kein Lernplan vorhanden.</p>
        ) : (
          <ul className="list-inside list-disc">
            {topics.map((topic) => (
              <li key={topic}>{topic}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
