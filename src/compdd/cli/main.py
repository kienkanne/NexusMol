import argparse
from pathlib import Path
from compdd.config import load_config


def add_config_arg(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to config YAML file",
    )
    return parser


def main():
    parser = argparse.ArgumentParser(prog="compdd", description="Computational tools for drug discovery")
    subparsers = parser.add_subparsers(dest="command", required=True)

    vina_parser = subparsers.add_parser("vina", help="Full Vina docking pipeline")
    add_config_arg(vina_parser)

    dock6_parser = subparsers.add_parser("dock6", help="Full DOCK6 docking pipeline")
    add_config_arg(dock6_parser)

    amber_md_parser = subparsers.add_parser("amber_md", help="Full AMBER molecular dynamics pipeline")
    add_config_arg(amber_md_parser)

    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.command == "vina":
        from compdd.vina.vina_pipeline import VinaPipeline
        VinaPipeline(cfg).run()
        return True

    elif args.command == "dock6":
        from compdd.dock6.dock6_pipeline import DOCK6Pipeline
        DOCK6Pipeline(cfg).run()
        return True

    elif args.command == "amber_md":
        return False  

if __name__ == "__main__":
    main()