"""Command line entry point."""
import argparse

from shop import report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals")
    rep.add_argument("path")
    args = parser.parse_args(argv)
    if args.command == "report":
        print(report.render_text(report.summarize_file(args.path)))
    return 0
