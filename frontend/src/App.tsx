import { NavLink, Route, Routes } from "react-router-dom";

import { SpeechProvider } from "./audio/SpeechContext";
import ChatView from "./ChatView";
import { TransliterationProvider } from "./course/TransliterationContext";
import ProfileView from "./ProfileView";
import CourseView from "./views/CourseView";
import ReviewView from "./views/ReviewView";
import ScreeningView from "./views/ScreeningView";
import UnitView from "./views/UnitView";

const TABS = [
  { to: "/kurs", label: "Kurs" },
  { to: "/wiederholen", label: "Wiederholen" },
  { to: "/profil", label: "Profil" },
];

export default function App() {
  return (
    <TransliterationProvider>
      <SpeechProvider>
        <div className="min-h-screen bg-slate-50 text-slate-900">
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex max-w-3xl items-center gap-6 px-4 py-3">
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
            </div>
          </header>
          <main className="mx-auto max-w-3xl px-4 py-6">
            <Routes>
              <Route path="/" element={<CourseView />} />
              <Route path="/kurs" element={<CourseView />} />
              <Route path="/kurs/:unitId" element={<UnitView />} />
              <Route path="/einstufung" element={<ScreeningView />} />
              <Route path="/wiederholen" element={<ReviewView />} />
              <Route path="/profil" element={<ProfileView />} />
              <Route path="/gespraech" element={<ChatView />} />
            </Routes>
          </main>
        </div>
      </SpeechProvider>
    </TransliterationProvider>
  );
}
