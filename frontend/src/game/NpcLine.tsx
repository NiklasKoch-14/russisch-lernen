import SpeakerButton from "../audio/SpeakerButton";
import RussianText from "../course/RussianText";
import type { SpokenLine } from "../gameTypes";

export default function NpcLine({ line, name }: { line: SpokenLine; name?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-2xl bg-slate-100 p-3">
      <div className="flex-1">
        {name && <p className="text-sm font-medium text-slate-500">{name}</p>}
        <RussianText word={{ text: line.text, translit: line.translit }} />
      </div>
      <SpeakerButton text={line.audio_text} />
    </div>
  );
}
