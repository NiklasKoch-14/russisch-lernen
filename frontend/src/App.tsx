import { NavLink, Route, Routes, useLocation } from "react-router-dom";

import AutoplayToggle from "./audio/AutoplayToggle";
import { SpeechProvider } from "./audio/SpeechContext";
import ChatView from "./ChatView";
import { TransliterationProvider } from "./course/TransliterationContext";
import ProfileView from "./ProfileView";
import CourseView from "./views/CourseView";
import FlashcardsView from "./views/FlashcardsView";
import ListeningView from "./views/ListeningView";
import PlaceView from "./views/PlaceView";
import ReviewView from "./views/ReviewView";
import SceneView from "./views/SceneView";
import ScreeningView from "./views/ScreeningView";
import TodayView from "./views/TodayView";
import UnitView from "./views/UnitView";
import VillageView from "./views/VillageView";

// "Heute" ist die Startseite und steht deshalb vorn. `end`, weil "/" sonst
// zu jeder Adresse passt und der Reiter immer markiert waere.
const TABS = [
  { to: "/", label: "Heute", end: true },
  { to: "/kurs", label: "Kurs" },
  { to: "/dorf", label: "Dorf" },
  { to: "/hoeren", label: "Hören" },
  { to: "/karten", label: "Karten" },
  { to: "/wiederholen", label: "Wiederholen" },
  { to: "/profil", label: "Profil" },
];

const WIDE_PREFIX = "/dorf";

export default function App() {
  const { pathname } = useLocation();
  // Das Dorf ist eine Karte und braucht Platz. Fliesstext bleibt schmal:
  // ueber die volle Breite gezogen liest er sich schlechter, nicht besser.
  // Nur "/dorf" selbst und seine Unterrouten zaehlen — ein Pfad wie
  // "/dorfmarkt" soll nicht versehentlich die volle Breite bekommen.
  const wide = pathname === WIDE_PREFIX || pathname.startsWith(`${WIDE_PREFIX}/`);

  return (
    <TransliterationProvider>
      <SpeechProvider>
        {/* Im Dorf fuellt die Seite genau den Bildschirm: die Karte und die
            Raeume sind Bilder, und wer ein Haus betritt, soll ohne Scrollen
            wieder hinausfinden. Auf schmalen Fenstern bleibt der gewohnte
            Fliesstext-Fluss, sonst wird es dort zu eng. */}
        <div
          className={`bg-slate-50 text-slate-900 ${
            wide
              ? "min-h-screen sm:relative sm:flex sm:h-dvh sm:min-h-0 sm:flex-col sm:overflow-hidden"
              : "min-h-screen"
          }`}
        >
          <header
            className={
              wide
                ? // Ueber dem Bild statt darueber gestapelt: der Raum soll den
                  // ganzen Platz bekommen, die Navigation bleibt trotzdem
                  // sichtbar — so wollte es der Nutzer.
                  "border-b border-slate-200 bg-white sm:absolute sm:inset-x-0 sm:top-0 sm:z-20 sm:border-0 sm:bg-white/75 sm:backdrop-blur"
                : "border-b border-slate-200 bg-white"
            }
          >
            {/* Der Inhalt steht überall gleich mittig, auch im Dorf: dort wird
                nur der Hintergrund breit, damit die Navigation beim Wechsel
                nicht an den Rand springt. */}
            <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
              <span className="text-lg font-semibold">Russisch lernen</span>
              {/* Sieben Reiter passen auf dem Handy nicht in eine Zeile — ohne
                  Umbruch liefe die ganze Seite seitlich aus dem Bild. */}
              <nav className="flex flex-wrap gap-x-4 gap-y-1">
                {TABS.map((tab) => (
                  <NavLink
                    key={tab.to}
                    to={tab.to}
                    end={tab.end}
                    className={({ isActive }) =>
                      isActive ? "font-medium text-sky-700" : "text-slate-600 hover:text-slate-900"
                    }
                  >
                    {tab.label}
                  </NavLink>
                ))}
              </nav>
              <div className="ml-auto">
                <AutoplayToggle />
              </div>
            </div>
          </header>
          <main
            className={
              wide
                ? "px-4 py-6 sm:flex sm:min-h-0 sm:flex-1 sm:flex-col sm:p-0"
                : "mx-auto max-w-3xl px-4 py-6"
            }
          >
            <Routes>
              <Route path="/" element={<TodayView />} />
              <Route path="/kurs" element={<CourseView />} />
              <Route path="/kurs/:unitId" element={<UnitView />} />
              <Route path="/einstufung" element={<ScreeningView />} />
              <Route path="/hoeren" element={<ListeningView />} />
              <Route path="/karten" element={<FlashcardsView />} />
              <Route path="/wiederholen" element={<ReviewView />} />
              <Route path="/profil" element={<ProfileView />} />
              <Route path="/gespraech" element={<ChatView />} />
              <Route path="/dorf" element={<VillageView />} />
              <Route path="/dorf/:placeId" element={<PlaceView />} />
              <Route path="/dorf/:placeId/szene/:sceneId" element={<SceneView />} />
            </Routes>
          </main>
        </div>
      </SpeechProvider>
    </TransliterationProvider>
  );
}
