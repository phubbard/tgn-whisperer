import argparse
import logging
from rich.logging import RichHandler
from .scrape import run

def build_parser():
    p = argparse.ArgumentParser(
        prog="collect-related-links",
        description="Extract related links (Substack-friendly), resolve redirectors, and emit JSONL."
    )
    p.add_argument("urls", help="Path to a text file with one URL per line.")
    p.add_argument("--out", default="related.jsonl", help="Output JSONL file (default: related.jsonl)")
    p.add_argument("--exceptions", default="exceptions.jsonl", help="Exceptions JSONL file (default: exceptions.jsonl)")
    p.add_argument("--overrides", default=None, help="Optional YAML of per-domain CSS selectors")
    p.add_argument("--rate", type=float, default=1.2, help="Per-domain polite delay in seconds (default: 1.2)")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"], help="Console log level")
    return p

def main():
    args = build_parser().parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    log = logging.getLogger("collector")

    run(
        urls_path=args.urls,
        out_path=args.out,
        exceptions_path=args.exceptions,
        overrides_path=args.overrides,
        rate=args.rate,
        log=log
    )

if __name__ == "__main__":
    main()
