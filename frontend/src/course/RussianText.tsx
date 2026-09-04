import type { Word } from "../courseTypes";
import { useTransliteration } from "./TransliterationContext";

export default function RussianText({ word, className = "" }: { word: Word; className?: string }) {
  const { show } = useTransliteration();
  return (
    <span className={`inline-flex flex-col items-center leading-tight ${className}`}>
      <span lang="ru">{word.text}</span>
      {show && word.translit ? <span className="text-xs text-slate-500">{word.translit}</span> : null}
    </span>
  );
}
