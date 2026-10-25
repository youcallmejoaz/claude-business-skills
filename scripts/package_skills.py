"""Zip each skill folder for upload to Claude: dist/<skill>.zip."""

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    for skill in sorted((ROOT / "skills").iterdir()):
        out = dist / f"{skill.name}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(skill.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    z.write(f, f.relative_to(skill.parent))
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
