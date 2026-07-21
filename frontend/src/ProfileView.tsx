import { useEffect, useState } from "react";
import { getLearningPlan, getProfile } from "./api";

export default function ProfileView() {
  const [level, setLevel] = useState<string | null>(null);
  const [topics, setTopics] = useState<string[]>([]);

  useEffect(() => {
    getProfile().then((profile) => setLevel(profile.cefr_level));
    getLearningPlan().then((plan) => setTopics(plan?.topics ?? []));
  }, []);

  return (
    <div>
      <p>Aktuelles Level: {level ?? "wird ermittelt..."}</p>
      <h2>Aktueller Lernplan</h2>
      {topics.length === 0 ? (
        <p>Noch kein Lernplan vorhanden.</p>
      ) : (
        <ul>
          {topics.map((topic) => (
            <li key={topic}>{topic}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
