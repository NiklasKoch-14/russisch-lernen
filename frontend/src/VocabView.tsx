import { useEffect, useState } from "react";
import { answerVocabCard, getDueCards } from "./api";
import type { VocabCard } from "./api";

export default function VocabView() {
  const [cards, setCards] = useState<VocabCard[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<"correct" | "incorrect" | null>(null);

  useEffect(() => {
    getDueCards().then(setCards);
  }, []);

  const currentCard = cards[index];

  async function handleSubmit() {
    if (!currentCard) return;
    const result = await answerVocabCard(currentCard.id, answer);
    setFeedback(result.correct ? "correct" : "incorrect");
  }

  function handleNext() {
    setFeedback(null);
    setAnswer("");
    setIndex((i) => i + 1);
  }

  if (cards.length === 0) {
    return <p>Keine fälligen Karteikarten.</p>;
  }

  if (!currentCard) {
    return <p>Alle fälligen Karten erledigt!</p>;
  }

  return (
    <div>
      <p>{currentCard.term}</p>
      {feedback === null ? (
        <>
          <input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Übersetzung eingeben..."
          />
          <button onClick={handleSubmit}>Prüfen</button>
        </>
      ) : (
        <>
          <p>{feedback === "correct" ? "Richtig!" : `Falsch. Richtig wäre: ${currentCard.translation}`}</p>
          <button onClick={handleNext}>Weiter</button>
        </>
      )}
    </div>
  );
}
