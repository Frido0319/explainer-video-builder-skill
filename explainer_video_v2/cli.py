"""Command line entry point for Explainer Video Builder V2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_project, prepare_project
from .verify import verify_project


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "build", "verify"))
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.command == "validate":
        data = prepare_project(args.manifest)
        print(
            f"清单验证通过：mode={data['mode']} theme={data['theme']} duration={data['duration']}s"
        )
    elif args.command == "build":
        print(f"成片输出：{build_project(args.manifest)}")
    else:
        print(json.dumps(verify_project(args.manifest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
