"""Render newsletter content + brand config into a final, CSS-inlined HTML file.

Usage:
    python tools/build_newsletter_html.py --content PATH [--brand PATH] [--out PATH]

Content JSON shape:
{
  "headline": "...",
  "intro": "... (optional)",
  "sections": [
    {
      "heading": "...",
      "body_html": "<p>...</p>",
      "stats": [ {"value": "91%", "label": "..."} ],           (optional, native HTML stat tiles)
      "infographic": {"src": "...", "alt": "...", "caption": "..."}  (optional, one image for this section)
    }
  ],
  "sources": [ {"title": "...", "url": "..."} ]
}
"""
import argparse
import base64
import json
import mimetypes
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from premailer import transform

TEMPLATE_DIR = Path(__file__).parent / "templates"
DEFAULT_BRAND_PATH = Path("assets/brand/brand.json")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "newsletter"


def as_data_uri(path_str: str) -> str:
    """Embed a local image file as a base64 data URI so the final HTML is
    self-contained (works whether opened locally or sent via email, where a
    relative/local file path wouldn't resolve). Leaves http(s)/data URLs as-is."""
    if not path_str or path_str.startswith(("http://", "https://", "data:")):
        return path_str
    image_path = Path(path_str)
    if not image_path.exists():
        return path_str
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    return f"data:{mime_type};base64,{encoded}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the final newsletter HTML")
    parser.add_argument("--content", required=True, help="Path to content JSON")
    parser.add_argument("--brand", default=str(DEFAULT_BRAND_PATH), help="Path to brand.json")
    parser.add_argument("--out", default=None, help="Output HTML path (default: .tmp/newsletter_<slug>.html)")
    args = parser.parse_args()

    content = json.loads(Path(args.content).read_text(encoding="utf-8"))
    brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))

    brand["logo_url"] = as_data_uri(brand.get("logo_url", ""))
    for section in content.get("sections", []):
        if section.get("infographic"):
            section["infographic"]["src"] = as_data_uri(section["infographic"]["src"])

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("newsletter_template.html")

    raw_html = template.render(brand=brand, **content)
    inlined_html = transform(raw_html, remove_classes=True)

    out_path = Path(args.out) if args.out else Path(".tmp") / f"newsletter_{slugify(content['headline'])}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(inlined_html, encoding="utf-8")

    print(str(out_path))


if __name__ == "__main__":
    main()
