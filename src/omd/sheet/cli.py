"""`omd-sheet` command-line interface.

The tool is data-free: real models are Python *spec* modules that import the builder (see
``README.md``). The CLI covers the two things that make sense without a spec file — building
the built-in synthetic reference model, and verifying it — so a consumer can prove the install
works end-to-end on their machine / CI.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="omd-sheet",
        description="Reusable FAST spreadsheet generator (house formatting + self-verify harness).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("demo", help="build the synthetic reference workbook")
    d.add_argument("--out", "-o", required=True, metavar="PATH", help="output .xlsx path")

    v = sub.add_parser(
        "verify", help="build the synthetic reference workbook and verify its formulas"
    )
    v.add_argument(
        "--out",
        "-o",
        default=None,
        metavar="PATH",
        help="optional path to keep the built .xlsx (default: a temp file)",
    )

    args = parser.parse_args(argv)

    if args.command == "demo":
        from .example import build_reference

        build_reference(args.out)
        print("OK  ->", args.out)
        return 0

    if args.command == "verify":
        import tempfile
        from pathlib import Path

        from .example import verify_reference

        if args.out:
            verify_reference(args.out)
            print("VERIFIED  ->", args.out)
        else:
            with tempfile.TemporaryDirectory() as td:
                verify_reference(str(Path(td) / "reference.xlsx"))
            print(
                "VERIFIED  (synthetic reference model: live formulas reproduce Python source-of-truth)"
            )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
