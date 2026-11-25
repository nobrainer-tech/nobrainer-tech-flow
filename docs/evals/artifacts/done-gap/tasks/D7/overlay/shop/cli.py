"""Command line entry point."""
import argparse

from shop import report, stream_report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals")
    rep.add_argument("path")
    args = parser.parse_args(argv)
    if args.command == "report":
        summary = stream_report.summarize_path(args.path)
        print(report.render_text(summary))
    return 0
