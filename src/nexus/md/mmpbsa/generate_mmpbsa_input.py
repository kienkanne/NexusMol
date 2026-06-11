from nexus.md.mmpbsa.mmpbsa_config import MMPBSAConfig


def generate_mmpbsa_input(cfg: MMPBSAConfig):
    mmpbsa_input = []
    mmpbsa_input.extend([
        "&general",
        f"startframe={cfg.common.start_frame},",
        f"endframe={cfg.common.end_frame},",
        f"interval={cfg.common.interval},",
        "verbose=1,",
        "keep_files=0,",
        "/"
    ])

    if not (cfg.gb.run or cfg.pb.run):
        raise ValueError("At least gb or pb must have run: True")

    if cfg.gb.run:
        mmpbsa_input.extend([
        "&gb",
        f"igb={cfg.gb.igb},",
        f"saltcon={cfg.gb.saltcon},",
        "/"      
        ])

    if cfg.pb.run:
        mmpbsa_input.extend([
        "&pb",
        f"istrng={cfg.pb.istrng},",
        f"fillratio={cfg.pb.fillratio},",
        "/"      
        ])     

    if cfg.decomp.run:
        mmpbsa_input.extend([
        "&decomp",
        f"idecomp={cfg.decomp.idecomp},",
        "dec_verbose=1",
        "/"      
        ])

    mmpbsa_input = "\n".join(mmpbsa_input)

    return mmpbsa_input
