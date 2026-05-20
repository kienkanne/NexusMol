import argparse
from pathlib import Path
from compdd.configs.root_config import load_config


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


    vina_parser = subparsers.add_parser("run_vina", help="Full Vina docking pipeline")
    add_config_arg(vina_parser)

    validate_vina_parser = subparsers.add_parser("validate_run_vina", help="Run validation Vina pipeline")
    add_config_arg(validate_vina_parser)


    dock6_parser = subparsers.add_parser("run_dock6", help="Full DOCK6 docking pipeline")
    add_config_arg(dock6_parser)

    validate_dock6_parser = subparsers.add_parser("validate_run_dock6", help="Run validation DOCK6 pipeline")
    add_config_arg(validate_dock6_parser)


    amber_md_parser = subparsers.add_parser("amber_md", help="Full AMBER molecular dynamics pipeline")
    add_config_arg(amber_md_parser)

    args = parser.parse_args()

    if args.command == "run_vina":
        from compdd.vina.vina_pipeline import VinaPipeline

        cfg = load_config(args.config)
        VinaPipeline(cfg).run()
        return True

    elif args.command == "validate_run_vina":
        # Run the validation Vina pipeline using the existing validation loader and RMSD utilities
        from compdd.validation_coreset.validation_config import load_validation_config
        from compdd.validation_coreset.rmsd import compute_validation_rmsds
        from compdd.vina.vina_pipeline import VinaPipeline

        cfg = load_validation_config(args.config)
        cfg.common.program = "vina"
        VinaPipeline(cfg).run()
        compute_validation_rmsds(cfg)
        return True

    elif args.command == "validate_run_dock6":
        from compdd.validation_coreset.validation_config import load_validation_config
        from compdd.validation_coreset.rmsd import compute_validation_rmsds
        from compdd.dock6.dock6_pipeline import DOCK6Pipeline

        cfg = load_validation_config(args.config)
        cfg.common.program = "dock6"
        DOCK6Pipeline(cfg).run()
        compute_validation_rmsds(cfg)
        return True

    elif args.command == "run_dock6":
        from compdd.dock6.dock6_pipeline import DOCK6Pipeline

        cfg = load_config(args.config)
        DOCK6Pipeline(cfg).run()
        return True

    elif args.command == "validate_run_dock6":
        # Run the validation pipeline using the existing validation loader and RMSD utilities
        from compdd.validation_coreset.validation_config import load_validation_config
        from compdd.validation_coreset.rmsd import compute_validation_rmsds
        from compdd.dock6.dock6_pipeline import DOCK6Pipeline

        cfg = load_validation_config(args.config)
        cfg.common.program = "dock6"
        DOCK6Pipeline(cfg).run()
        compute_validation_rmsds(cfg)
        return True

    elif args.command == "amber_md":
        return False  


if __name__ == "__main__":
    main()
