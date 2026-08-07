from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.errors import MarketplaceError
from app.models import ExtractionResult
from app.services.export import save_csv, save_json
from app.services.extractor import extract_from_html, extract_from_url


def _str2bool(value: str) -> bool:
    return value.strip().lower() not in ("false", "0", "no")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.cli",
        description="Extract product and seller data from a marketplace page.",
    )
    parser.add_argument("--url", help="Product URL (used as source_url).")
    parser.add_argument("--file", help="Path to a saved HTML file to parse instead of downloading.")
    parser.add_argument("--output", help="Path to write the JSON result.")
    parser.add_argument(
        "--pretty", type=_str2bool, default=True, help="Pretty-print JSON output (default: true)."
    )
    parser.add_argument("--urls-file", help="Text file with one URL per line for batch mode.")
    parser.add_argument("--csv-output", help="Path to write batch results as CSV.")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between batch requests.")
    return parser


def _extract_one(url: str, file: str | None) -> ExtractionResult:
    if file:
        html = Path(file).read_text(encoding="utf-8")
        return extract_from_html(html, url)
    return extract_from_url(url)


def _run_single(args: argparse.Namespace) -> int:
    if not args.url:
        print("error: --url is required", file=sys.stderr)
        return 1
    try:
        result = _extract_one(args.url, args.file)
    except MarketplaceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2 if args.pretty else None))

    if args.output:
        save_json(result, Path(args.output), pretty=args.pretty)
        print(f"Saved to {args.output}", file=sys.stderr)

    return 0


def _run_batch(args: argparse.Namespace) -> int:
    urls_path = Path(args.urls_file)
    urls = [line.strip() for line in urls_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    results: list[ExtractionResult] = []
    for index, url in enumerate(urls):
        try:
            result = extract_from_url(url)
            results.append(result)
            print(json.dumps({"url": url, "status": "ok"}, ensure_ascii=False))
        except MarketplaceError as exc:
            print(json.dumps({"url": url, "status": "error", "error": str(exc)}, ensure_ascii=False))
        if index < len(urls) - 1:
            time.sleep(args.delay)

    if args.csv_output and results:
        save_csv(results, Path(args.csv_output))
        print(f"Saved {len(results)} results to {args.csv_output}", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.urls_file:
        return _run_batch(args)
    return _run_single(args)


if __name__ == "__main__":
    raise SystemExit(main())
