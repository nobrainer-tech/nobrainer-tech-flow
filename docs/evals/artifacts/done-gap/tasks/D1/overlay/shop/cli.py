"""Command line entry point."""
import argparse
import sys

from shop import invoice, report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals")
    rep.add_argument("path")
    inv = sub.add_parser("invoice", help="print the invoice of one order")
    inv.add_argument("order_id")
    args = parser.parse_args(argv)
    if args.command == "report":
        summary = report.summarize(report.load_totals(args.path))
        print(report.render_text(summary))
    elif args.command == "invoice":
        try:
            total = invoice.load_total(args.order_id)
        except KeyError:
            print(f"unknown order: {args.order_id}", file=sys.stderr)
            return 1
        print(invoice.render_invoice(args.order_id, total))
    return 0
