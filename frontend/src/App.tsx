import { useState } from "react";
import ChatView from "./ChatView";
import ProfileView from "./ProfileView";
import VocabView from "./VocabView";

type Tab = "chat" | "vocab" | "profile";

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div>
      <h1>Speaker</h1>
      <nav>
        <button onClick={() => setTab("chat")}>Dialog</button>
        <button onClick={() => setTab("vocab")}>Vokabeln</button>
        <button onClick={() => setTab("profile")}>Profil</button>
      </nav>
      {tab === "chat" && <ChatView />}
      {tab === "vocab" && <VocabView />}
      {tab === "profile" && <ProfileView />}
    </div>
  );
}
