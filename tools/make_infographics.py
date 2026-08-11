"""Generate an infographic/logo image via Pollinations.ai (free, no API key).

Google's Gemini API image models turned out to require a billing account
linked even for "free tier" usage (confirmed via a live 429/limit:0 test on
2026-08-11), so this uses Pollinations.ai instead: a fully free, no-signup,
no-key, open image generation API.

Usage:
    python tools/make_infographics.py "<image prompt>" [--width 1024] [--height 1024] [--out PATH]
"""
import argparse
import re
import urllib.parse
from pathlib import Path

import requests

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "infographic"


def generate(prompt: str, width: int, height: int, seed: int | None) -> bytes:
    url = POLLINATIONS_URL.format(prompt=urllib.parse.quote(prompt))
    params = {"width": width, "height": height, "nologo": "true", "model": "flux"}
    if seed is not None:
        params["seed"] = seed

    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()
    return response.content


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an image via Pollinations.ai")
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed for reproducible output")
    parser.add_argument("--out", default=None, help="Output image path (default: .tmp/infographics/<slug>.png)")
    args = parser.parse_args()

    image_bytes = generate(args.prompt, args.width, args.height, args.seed)

    out_path = Path(args.out) if args.out else Path(".tmp/infographics") / f"{slugify(args.prompt)}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)

    print(str(out_path))


if __name__ == "__main__":
    main()
