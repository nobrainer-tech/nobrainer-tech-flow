"""Command line entry point."""
import argparse

from shop import orders, report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals")
    rep.add_argument("path")
    sub.add_parser("return-reasons", help="print the allowed return reasons")
    args = parser.parse_args(argv)
    if args.command == "report":
        summary = report.summarize_rows(report.load_rows(args.path))
        print(report.render_text(summary))
    elif args.command == "return-reasons":
        for reason in orders.RETURN_REASONS:
            print(reason)
    return 0
