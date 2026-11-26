"""Command line entry point."""
import argparse

from shop import report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals")
    rep.add_argument("path")
    rep.add_argument("--top", type=int, metavar="N", help="also print the N largest orders")
    args = parser.parse_args(argv)
    if args.command == "report":
        orders = report.load_orders(args.path)
        print(report.render_text(report.summarize([total for _, total in orders])))
        if args.top:
            print(report.render_top(report.top_orders(orders, args.top)))
    return 0
