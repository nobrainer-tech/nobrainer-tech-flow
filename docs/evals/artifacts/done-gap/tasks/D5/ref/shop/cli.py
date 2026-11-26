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
    inv.add_argument("--html", action="store_true", help="write invoices/ORDER_ID.html instead")
    args = parser.parse_args(argv)
    if args.command == "report":
        summary = report.summarize(report.load_totals(args.path))
        print(report.render_text(summary))
    elif args.command == "invoice":
        try:
            order = invoice.load_order(args.order_id)
        except KeyError:
            print(f"unknown order: {args.order_id}", file=sys.stderr)
            return 1
        if args.html:
            print(invoice.write_html(args.order_id))
        else:
            print(invoice.render_invoice(args.order_id, float(order["total"])))
    return 0
