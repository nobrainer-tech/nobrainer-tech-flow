"""Command line entry point."""
import argparse

from shop import migrate, report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals")
    rep.add_argument("path")
    mig = sub.add_parser("migrate", help="upgrade order files to schema v2")
    mig.add_argument("directory")
    args = parser.parse_args(argv)
    if args.command == "report":
        summary = report.summarize(report.load_totals(args.path))
        print(report.render_text(summary))
    elif args.command == "migrate":
        migrated, failed = migrate.migrate_dir(args.directory)
        print(f"migrated {migrated} files, {len(failed)} failed")
        return 1 if failed else 0
    return 0
