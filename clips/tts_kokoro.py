"""Generate one WAV per proposal-cut scene with Kokoro TTS (run with a Python that has kokoro-onnx).

    python clips/tts_kokoro.py <dir with kokoro-v1.0.onnx and voices-v1.0.bin>
Writes clips/voice/scene1.wav ... scene7.wav. Voice am_michael (fallback am_adam), speed 1.0.
"""

import re
import sys
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

HERE = Path(__file__).resolve().parent


def narration() -> list[str]:
    rows = []
    for line in (HERE / "proposal_cut_script.md").read_text().splitlines():
        m = re.match(r"^\| (\d) \| [^|]+ \| (.+) \|$", line)
        if m:
            rows.append(m.group(2).strip())
    return rows


def main() -> None:
    models = Path(sys.argv[1])
    k = Kokoro(str(models / "kokoro-v1.0.onnx"), str(models / "voices-v1.0.bin"))
    voice = "am_michael" if "am_michael" in k.get_voices() else "am_adam"
    out = HERE / "voice"
    out.mkdir(exist_ok=True)
    for i, text in enumerate(narration(), start=1):
        samples, rate = k.create(text, voice=voice, speed=1.0, lang="en-us")
        sf.write(out / f"scene{i}.wav", samples, rate)
        print(f"scene{i}: {len(samples) / rate:.2f}s ({voice})")


if __name__ == "__main__":
    main()
