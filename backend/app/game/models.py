from dataclasses import dataclass, field

from app.content.models import TokenRef


@dataclass(frozen=True)
class Hotspot:
    """Klickfläche als Anteil der Kartenbreite und -höhe, Bezugsformat 16:9."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Place:
    id: str
    name_ru: str
    name_de: str
    kind: str
    """course = führt in die nächste Einheit, npcs = Personenauswahl, shopping = Einkaufszettel."""
    art: str
    hotspot: Hotspot


@dataclass(frozen=True)
class Npc:
    id: str
    name_ru: str
    name_de: str
    place: str
    about_de: str
    art: str


@dataclass(frozen=True)
class Turn:
    npc_line: list[TokenRef]
    prompt_de: str
    solution: list[TokenRef]
    distractors: list[TokenRef]


@dataclass(frozen=True)
class AskTemplate:
    """Vorlage für einen Einkaufszug. None in `solution` ist der Platz der Ware."""

    npc_line: list[TokenRef]
    prompt_de: str
    solution: list[TokenRef | None]


@dataclass(frozen=True)
class Scene:
    id: str
    kind: str
    """dialog = ausgeschriebene Züge, shopping = aus dem Pool zusammengesetzt."""
    place: str
    npc: str
    title_de: str
    hint_unit: int
    intro_de: str = ""
    outro_de: str = ""
    turns: list[Turn] = field(default_factory=list)
    count: int = 0
    pool: list[TokenRef] = field(default_factory=list)
    ask_template: AskTemplate | None = None
    closing_turn: Turn | None = None


@dataclass(frozen=True)
class Village:
    places: dict[str, Place]
    npcs: dict[str, Npc]
    scenes: dict[str, Scene]

    def npcs_at(self, place_id: str) -> list[Npc]:
        return [npc for npc in self.npcs.values() if npc.place == place_id]

    def scenes_at(self, place_id: str, npc_id: str | None = None) -> list[Scene]:
        return [
            scene
            for scene in self.scenes.values()
            if scene.place == place_id and (npc_id is None or scene.npc == npc_id)
        ]
