import argparse
from pathlib import Path

from compdd.validation.config import load_validation_config
from compdd.validation.pipeline import ValidationPipeline


def add_config_arg(parser):
    parser.add_argument("--config", type=Path, required=True, help="Path to validation YAML config")
    return parser


def main():
    parser = argparse.ArgumentParser(prog="validate", description="CompDD CASF validation workflows")
    subparsers = parser.add_subparsers(dest="command", required=True)

    vina_parser = subparsers.add_parser("run_vina", help="Validate the Vina pipeline")
    add_config_arg(vina_parser)

    dock6_parser = subparsers.add_parser("run_dock6", help="Validate the DOCK6 pipeline")
    add_config_arg(dock6_parser)

    args = parser.parse_args()
    cfg = load_validation_config(args.config)

    if args.command == "run_vina":
        return ValidationPipeline(cfg, program="vina").run()
    if args.command == "run_dock6":
        return ValidationPipeline(cfg, program="dock6").run()

    return None


if __name__ == "__main__":
    main()
