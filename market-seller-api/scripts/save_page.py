from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.errors import MarketplaceError
from app.services.fetcher import fetch_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download a page and save it to disk for offline development."
    )
    parser.add_argument("url", help="URL of the page to download.")
    parser.add_argument("--output", required=True, help="Path to write the downloaded HTML.")
    args = parser.parse_args(argv)

    try:
        html = fetch_html(args.url)
    except MarketplaceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Saved {len(html)} characters to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
