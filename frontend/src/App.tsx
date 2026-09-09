import { NavLink, Route, Routes, useLocation } from "react-router-dom";

import AutoplayToggle from "./audio/AutoplayToggle";
import { SpeechProvider } from "./audio/SpeechContext";
import ChatView from "./ChatView";
import { TransliterationProvider } from "./course/TransliterationContext";
import ProfileView from "./ProfileView";
import CourseView from "./views/CourseView";
import PlaceView from "./views/PlaceView";
import ReviewView from "./views/ReviewView";
import SceneView from "./views/SceneView";
import ScreeningView from "./views/ScreeningView";
import UnitView from "./views/UnitView";
import VillageView from "./views/VillageView";

const TABS = [
  { to: "/kurs", label: "Kurs" },
  { to: "/dorf", label: "Dorf" },
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
            <div
              className={
                wide
                  ? "flex items-center gap-6 px-4 py-3"
                  : "mx-auto flex max-w-3xl items-center gap-6 px-4 py-3"
              }
            >
              <span className="text-lg font-semibold">Speaker</span>
              <nav className="flex gap-4">
                {TABS.map((tab) => (
                  <NavLink
                    key={tab.to}
                    to={tab.to}
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
              <Route path="/" element={<CourseView />} />
              <Route path="/kurs" element={<CourseView />} />
              <Route path="/kurs/:unitId" element={<UnitView />} />
              <Route path="/einstufung" element={<ScreeningView />} />
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
