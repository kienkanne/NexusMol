from nexus.md.analyze.analyze_config import AnalyzeConfig

# TODO: Copy important output files to output_dir. Currently output_dir only contains figures.
def generate_cpptraj_input(cfg: AnalyzeConfig):
    name = cfg.common.job_name
    prmtop = str(cfg.common.prmtop)
    trajin = str(cfg.common.trajin)
    receptor_mask = cfg.common.receptor_mask
    n_clusters = cfg.cluster.n_cluster
    n_eigen = cfg.pca.n_eigen

    lines = []
    outputs = {}

    lines.extend([
        f"parm {prmtop}",
        f"trajin {trajin}",
        "autoimage",
    ])

    rmsd_out = f"rmsd_{name}.dat"
    rmsf_out = f"rmsf_{name}.dat"
    outputs["rmsd_out"] = rmsd_out
    outputs["rmsf_out"] = rmsf_out

    if cfg.rms.rms_option == "alpha":
        lines.extend([
        f"rmsd first {receptor_mask}@CA out {rmsd_out}",
        f"atomicfluct out {rmsf_out} @CA byres"
        ])
    elif cfg.rms.rms_option == "backbone":
        lines.extend([
        f"rmsd first {receptor_mask}@CA,C,N out {rmsd_out}",
        f"atomicfluct out {rmsf_out} @CA,C,N byres"
        ])       
    lines.append("run")

    hb = cfg.hbonds
    if hb and (hb.pp or hb.pw or hb.bb or hb.pl):
        hb_block = []
        if hb.pp:
            PP_hbvtime = f"PP_hbvtime_{name}.dat"
            PP_avg = f"PP_avg_{name}.dat"
            outputs["PP_hbvtime"] = PP_hbvtime
            outputs["PP_avg"] = PP_avg

            hb_block.extend([f"hbond ProtProt {receptor_mask} out {PP_hbvtime} avgout {PP_avg}"])
        if hb.pw:
            PW_avg = f"PW_avg_{name}.dat"
            Bridge_avg = f"Bridge_avg_{name}.dat"
            outputs["PW_avg"] = PW_avg
            outputs["Bridge_avg"] = Bridge_avg

            hb_block.extend([
                f"hbond All {receptor_mask} solventdonor :WAT solventacceptor :WAT@O solvout {PW_avg} bridgeout {Bridge_avg}",
                # Only strip out solvent after protein-water analysis
                "strip :Na+,Cl-,WAT",
            ])
        if hb.bb:
            BB_avg = f"BB_avg_{name}.dat"
            outputs["BB_avg"] = BB_avg

            hb_block.extend([f"hbond BB_Prot {receptor_mask}@N,H,O donormask {receptor_mask}@N,H acceptormask {receptor_mask}@O avgout {BB_avg}"])
        if hb.pl:
            PtoL_avg = f"PtoL_avg_{name}.dat"
            LtoP_avg = f"LtoP_avg_{name}.dat"
            outputs["PtoL_avg"] = PtoL_avg
            outputs["LtoP_avg"] = LtoP_avg

            hb_block.extend([
                "hbond ProtLig_PL \\",
                f"    donormask {receptor_mask} \\",
                f"    acceptormask !({receptor_mask}) \\",
                f"    avgout {PtoL_avg}",
                "hbond ProtLig_LP \\",
                f"    donormask !({receptor_mask}) \\",
                f"    acceptormask {receptor_mask} \\",
                f"    avgout {LtoP_avg}",
            ])

        hb_block.append("run")

        if hb.pw:
            PW_hbvtime = f"PW_hbvtime_{name}.dat"
            outputs["PW_hbvtime"] = PW_hbvtime
            Bridge_hvtime = f"Bridge_hbvtime_{name}.dat"
            outputs["Bridge_hvtime"] = Bridge_hvtime

            hb_block.extend([f"create {PW_hbvtime} All[UV]", f"create Bridge_hbvtime_{name}.dat All[Bridge]"])
        if hb.bb:
            BB_hbvtime = f"BB_hbvtime_{name}.dat"
            outputs["BB_hbvtime"] = BB_hbvtime

            hb_block.append(f"create {BB_hbvtime} BB_Prot[UU]")
        if hb.pl:
            PL_all_hbvtime = f"PL_all_hbvtime_{name}.dat"
            outputs["PL_all_hbvtime"] = PL_all_hbvtime

            hb_block.extend(["ProtLig_All = ProtLig_PL[UU] + ProtLig_LP[UU]", f"create {PL_all_hbvtime} ProtLig_All"])

        hb_block.append("run")

        lines.extend(hb_block)

    if cfg.ss.run:
        ss_sumout = f"ss_sumout_{name}.dat"
        ss_totalout = f"ss_totalout_{name}.dat"
        outputs["ss_sumout"] = ss_sumout
        outputs["ss_totalout"] = ss_totalout

        lines.extend([
            f"secstruct sumout {ss_sumout} totalout {ss_totalout}",
            "run",
        ])

    if cfg.pca.run:
        pca_out = f"pca_{name}.dat"
        outputs["pca_out"] = pca_out

        lines.extend([
            "strip :Na+,Cl-,WAT",
            "average @N,C,CA crdset trajaverage",
            "createcrd trajectory",
            "run",
            f"crdaction trajectory rms ref trajaverage @N,C,CA",
            f"crdaction trajectory matrix covar name covmatrix @N,C,CA",
            f"runanalysis diagmatrix covmatrix out evecs_{name}.dat vecs {n_eigen} name eigenvectors",
            f"crdaction trajectory projection modes eigenvectors beg 1 end {n_eigen} @N,C,CA out {pca_out}",
            "run",
        ])

    if cfg.cluster.run:
        cnumvtime = f"cnumvtime_{name}.dat"
        cpopvtime = f"cpopvtime_{name}.dat"
        csummary = f"csummary_{name}.dat"
        outputs["cnumvtime"] = cnumvtime
        outputs["cpopvtime"] = cpopvtime
        outputs["csummary"] = csummary

        lines.extend([
            "strip :Na+,Cl-,WAT",
            "cluster c1 \\",
            f" kmeans clusters {n_clusters} randompoint maxit 500 \\",
            " sieve 10 random \\",
            f" out {cnumvtime} \\",
            f" summary {csummary} \\",
            f" cpopvtime {cpopvtime} normframe \\",
            f" info cinfo_{name}.dat \\",
            f" repout crep_{name} repfmt pdb \\",
            f" avgout cavg_{name} avgfmt pdb",
            "run",
        ])

    lines.append("quit")
    cpptraj_input = "\n".join(lines)

    return cpptraj_input, outputs
