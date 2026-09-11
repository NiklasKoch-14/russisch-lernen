"""Mehrere Sätze zu einer Tonspur zusammensetzen — ein Hörgespräch am Stück.

Einzeln nacheinander abgespielt, brach im Browser jede Zeile die vorige ab:
`audio.play()` meldet sich beim Start, nicht am Ende. Eine Spur hat dieses
Problem nicht, ist vorab vollständig geladen und kennt ihre Länge — der
Player kann zeigen, wie lange das Gespräch noch dauert.
"""

import io
import wave


def join_wavs(parts: list[bytes], *, pause_seconds: float) -> tuple[bytes, list[float]]:
    """Die Sätze mit Stille dazwischen hintereinander; dazu, wann jeder beginnt.

    Alle Teile müssen dasselbe Format haben. Die Stimmen von Piper liefern
    heute alle 22 050 Hz mono — eine neue Stimme mit anderer Abtastrate soll
    laut scheitern, statt zu schnell oder zu langsam zu klingen.
    """
    if not parts:
        raise ValueError("Keine Zeilen für die Tonspur")

    params = None
    frames: list[bytes] = []
    starts: list[float] = []
    offset = 0
    for data in parts:
        with wave.open(io.BytesIO(data)) as line:
            current = (line.getnchannels(), line.getsampwidth(), line.getframerate())
            if params is None:
                params = current
            elif current != params:
                raise ValueError(f"Format der Zeile passt nicht: {current} statt {params}")
            channels, width, rate = current
            if frames:
                silence = int(pause_seconds * rate)
                frames.append(b"\x00" * silence * channels * width)
                offset += silence
            starts.append(round(offset / rate, 3))
            count = line.getnframes()
            frames.append(line.readframes(count))
            offset += count

    assert params is not None
    channels, width, rate = params
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(width)
        out.setframerate(rate)
        out.writeframes(b"".join(frames))
    return buffer.getvalue(), starts
