"""Generate a minimal placeholder frog.ico for the Limnaion launcher.

This produces a 16x16 and 32x32 solid forest-green square encoded as an ICO
file.  It is PLACEHOLDER ART and must be replaced with real frog artwork
before the 1.0 release.

Run (from the repo root):
    python launcher/gen_frog_ico.py  # requires Pillow
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

# Forest green — placeholder colour chosen to be obviously non-final.
_COLOUR = (34, 139, 34, 255)
_OUT = Path(__file__).resolve().parent / "frog.ico"


def generate(out: Path = _OUT) -> None:
    """Write a valid multi-size ICO to *out*."""
    images = [Image.new("RGBA", (sz, sz), _COLOUR) for sz in (16, 32)]
    # Save as ICO; Pillow encodes each size as a PNG chunk inside the ICO.
    images[0].save(
        str(out),
        format="ICO",
        sizes=[(16, 16), (32, 32)],
        append_images=images[1:],
    )
    print(f"Written: {out}  ({out.stat().st_size} bytes)  [PLACEHOLDER — replace with real art]")


if __name__ == "__main__":
    generate()
