"""CLI entry point — argparse-based."""

from __future__ import annotations

import argparse
import json
import sys


def _cmd_report(args: argparse.Namespace) -> None:
    """Handle the 'report' command."""
    from .report import generate_report

    # Read input
    if args.file == "-":
        data = json.load(sys.stdin)
    else:
        try:
            with open(args.file) as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

    report = generate_report(data)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


def _cmd_validate(args: argparse.Namespace) -> None:
    """Handle the 'validate' command."""
    from .validate_cmd import validate_file

    is_valid, errors = validate_file(args.file, level=args.level)
    if is_valid:
        print(f"OK: {args.file} is valid at {args.level} level")
    else:
        print(f"INVALID: {args.file}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)


def _cmd_schema(args: argparse.Namespace) -> None:
    """Handle the 'schema' command."""
    from .validate_cmd import print_schema
    print_schema()


def cli() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="agentincident",
        description="AgentIncident CLI — incident reports and schema validation",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a 4-section incident report from a JSON file",
    )
    report_parser.add_argument(
        "file",
        help="Path to incident JSON file, or '-' for stdin",
    )
    report_parser.add_argument(
        "--output", "-o",
        help="Write report to file instead of stdout",
    )
    report_parser.set_defaults(func=_cmd_report)

    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an incident JSON file against the schema",
    )
    validate_parser.add_argument(
        "file",
        help="Path to incident JSON file, or '-' for stdin",
    )
    validate_parser.add_argument(
        "--level", "-l",
        choices=["core", "standard", "full"],
        default="core",
        help="Conformance level to validate against (default: core)",
    )
    validate_parser.set_defaults(func=_cmd_validate)

    # schema command
    schema_parser = subparsers.add_parser(
        "schema",
        help="Print the AgentIncident JSON schema to stdout",
    )
    schema_parser.set_defaults(func=_cmd_schema)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    cli()
