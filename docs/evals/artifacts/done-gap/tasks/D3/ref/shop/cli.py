"""Command line entry point."""
import argparse

from shop import report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals per currency")
    rep.add_argument("path")
    args = parser.parse_args(argv)
    if args.command == "report":
        blocks = report.summarize_by_currency(report.load_orders(args.path))
        print(report.render_blocks(blocks))
    return 0
