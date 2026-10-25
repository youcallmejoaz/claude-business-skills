"""Render clips/proposal_cut.mp4 from the Phase 3 clips and the scene voice files.

    python clips/make_proposal_cut.py           # uses clips/voice/scene1..7.wav if present
    python clips/make_proposal_cut.py --silent  # no voice

Rules (see proposal_cut_script.md): each scene lasts its narration plus 0.5 s (plus up to 1.5 s
of breathing room for UI scenes 2 to 6); clips are trimmed to fit or hold their last frame;
never faster than 1.25x; hard cuts, except a 0.3 s crossfade from a card into UI; a slow 5%
push-in on shots longer than 8 s; voice normalised to about -16 LUFS; no captions, no music.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
MAX_SPEED = 1.25
XFADE = 0.3

CLIPS = {p.name.split("_")[0]: p for p in HERE.glob("[CKP]0*.mp4")}

# (clip, in, out) windows per scene: the moments worth showing, in order.
SCENES = [
    {"segments": [("K01", 0.0, None)], "breathe": 0.0},
    {"segments": [("C01", 0.8, None), ("C02", 0.0, None)], "breathe": 1.5},
    {"segments": [("C03", 0.0, 3.6), ("C04", 1.8, None)], "breathe": 1.5},
    {"segments": [("C05", 0.8, 5.8), ("C05", 8.2, None)], "breathe": 1.5},
    {"segments": [("C06", 0.0, None)], "breathe": 1.5},
    {"segments": [("C07", 1.2, 5.5), ("K03", 1.2, 4.0)], "breathe": 1.5},
    {"segments": [("K04", 0.0, None)], "breathe": 0.0},
]


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd[:6])} ... failed:\n{r.stderr}")
    return r.stdout


def duration(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


def plan(voice: list[float | None]) -> list[dict]:
    """Work out each scene's length and each segment's speed, trim and hold."""
    out = []
    for i, scene in enumerate(SCENES):
        segs = []
        for clip, start, end in scene["segments"]:
            length = duration(CLIPS[clip])
            end = length if end is None else min(end, length)
            segs.append({"clip": clip, "in": start, "out": end})
        footage = sum(s["out"] - s["in"] for s in segs)
        if voice[i] is not None:
            target = voice[i] + 0.5 + scene["breathe"]
        else:
            target = min(footage, footage / MAX_SPEED + scene["breathe"])
        speed = min(MAX_SPEED, max(1.0, footage / target))
        # Too long even at the speed cap: trim each segment's tail in proportion.
        excess = footage / speed - target
        if excess > 0.01:
            for s in segs:
                share = (s["out"] - s["in"]) / footage
                s["out"] -= excess * speed * share
        hold = max(0.0, target - sum(s["out"] - s["in"] for s in segs) / speed)
        for s in segs:
            s["speed"] = speed
            s["dur"] = (s["out"] - s["in"]) / speed
        segs[-1]["dur"] += hold
        segs[-1]["hold"] = hold
        out.append({"scene": i + 1, "length": target, "speed": round(speed, 3), "segments": segs})
    return out


def render_segment(seg: dict, dest: Path, extra: float = 0.0) -> None:
    """One shot: trim, set speed, hold the last frame if needed, push in if long."""
    dur = seg["dur"] + extra
    hold = seg.get("hold", 0.0) + extra
    filters = [f"setpts=(PTS-STARTPTS)/{seg['speed']:.4f}", f"fps={FPS}"]
    if hold > 0:
        filters.append(f"tpad=stop_mode=clone:stop_duration={hold + 0.1:.3f}")
    if dur > 8:
        frames = int(dur * FPS)
        filters += ["scale=3840:2160:flags=lanczos",
                    f"zoompan=z='1+0.05*on/{frames}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps={FPS}"]
    filters.append("format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{seg['in']:.3f}", "-to", f"{seg['out']:.3f}",
         "-i", str(CLIPS[seg["clip"]]), "-vf", ",".join(filters), "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-an", str(dest)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--silent", action="store_true")
    args = ap.parse_args()
    wavs = [HERE / "voice" / f"scene{i}.wav" for i in range(1, len(SCENES) + 1)]
    voiced = not args.silent and all(w.exists() for w in wavs)
    voice = [duration(w) if voiced else None for w in wavs]
    scenes = plan(voice)

    tmp = Path(tempfile.mkdtemp(prefix="proposal-cut-"))
    parts = []
    for sc in scenes:
        for k, seg in enumerate(sc["segments"]):
            dest = tmp / f"s{sc['scene']}_{k}.mp4"
            # Scene 1 runs XFADE longer so the crossfade into scene 2 keeps scene 2 on its voice.
            render_segment(seg, dest, extra=XFADE if sc["scene"] == 1 else 0.0)
            parts.append(dest)

    # Video: crossfade card -> UI between scene 1 and 2, hard cuts everywhere else.
    inputs = sum((["-i", str(p)] for p in parts), [])
    first = duration(parts[0])
    norm = "".join(f"[{i}:v]settb=AVTB,setsar=1,fps={FPS}[n{i}];" for i in range(len(parts)))
    chain = norm + f"[n0][n1]xfade=transition=fade:duration={XFADE}:offset={first - XFADE:.3f}[x];"
    rest = "".join(f"[n{i}]" for i in range(2, len(parts)))
    chain += f"[x]{rest}concat=n={len(parts) - 1}:v=1:a=0[v]"
    video = tmp / "video.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", chain, "-map", "[v]",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", str(video)])
    total = duration(video)

    out = HERE / "proposal_cut.mp4"
    if voiced:
        # Each scene's voice starts at the scene start and is padded to the scene length.
        pads = "".join(f"[{i}:a]aresample=48000,apad=whole_dur={sc['length']:.3f}[a{i}];"
                       for i, sc in enumerate(scenes))
        joined = "".join(f"[a{i}]" for i in range(len(scenes)))
        joined_wav = tmp / "voice.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", *sum((["-i", str(w)] for w in wavs), []),
             "-filter_complex", pads + f"{joined}concat=n={len(scenes)}:v=0:a=1,highpass=f=70[a]",
             "-map", "[a]", str(joined_wav)])
        # Two-pass loudness normalisation to -16 LUFS.
        r = subprocess.run(["ffmpeg", "-i", str(joined_wav), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True)
        m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
        norm = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
        audio = tmp / "voice.m4a"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined_wav), "-af", f"{norm},aresample=48000",
             "-c:a", "aac", "-b:a", "192k", str(audio)])
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "copy", "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-c:v", "copy", "-movflags", "+faststart", str(out)])
    shutil.rmtree(tmp)

    (HERE / "proposal_cut_plan.json").write_text(json.dumps(
        {"voiced": voiced, "total_seconds": round(duration(out), 2), "scenes": scenes}, indent=2) + "\n")
    print(f"{out.name}: {duration(out):.1f}s, {'voice' if voiced else 'silent'}")
    for sc in scenes:
        segs = ", ".join(f"{s['clip']} {s['in']:.1f}-{s['out']:.1f}s x{s['speed']:.2f}"
                         + (f" +hold {s['hold']:.1f}s" if s.get("hold") else "") for s in sc["segments"])
        print(f"  scene {sc['scene']}: {sc['length']:.1f}s  {segs}")


if __name__ == "__main__":
    main()
