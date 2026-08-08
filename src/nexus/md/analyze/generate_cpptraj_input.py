from nexus.md.analyze.analyze_config import AnalyzeConfig

# TODO: Copy important output files to output_dir. Currently output_dir only contains figures.
def generate_cpptraj_input(cfg: AnalyzeConfig):
    name = cfg.common.job_name
    prmtop = str(cfg.common.prmtop)
    trajin = str(cfg.common.trajin)
    receptor_mask = cfg.common.receptor_mask
    pca_cluster_mask = cfg.common.pca_cluster_mask
    interval = cfg.common.interval
    n_clusters = cfg.cluster.n_cluster
    n_eigen = cfg.pca.n_eigen

    lines = []
    outputs = {}

    # Initialize and basic setup
    lines.extend([
        f"parm {prmtop}",
        f"trajin {trajin} 1 last {str(interval)}",
        "strip :Na+,Cl-,WAT",
        "autoimage",
        "rms first all",
    ])

    # 1. Structural metrics (RMSD/RMSF)
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

    # 2. Hydrogen Bonds (Setup Pass 1)
    hb = cfg.hbonds
    if hb and (hb.pp or hb.bb or hb.pl):
        if hb.pp:
            PP_hbvtime = f"PP_hbvtime_{name}.dat"
            PP_avg = f"PP_avg_{name}.dat"
            outputs["PP_hbvtime"] = PP_hbvtime
            outputs["PP_avg"] = PP_avg
            lines.append(f"hbond ProtProt {receptor_mask} out {PP_hbvtime} avgout {PP_avg}")

        if hb.bb:
            BB_avg = f"BB_avg_{name}.dat"
            outputs["BB_avg"] = BB_avg
            lines.append(f"hbond BB_Prot {receptor_mask}@N,H,O donormask {receptor_mask}@N,H acceptormask {receptor_mask}@O avgout {BB_avg}")
        
        ligand_mask = cfg.common.ligand_mask
        if hb.pl and ligand_mask is not None:
            PtoL_avg = f"PtoL_avg_{name}.dat"
            LtoP_avg = f"LtoP_avg_{name}.dat"
            outputs["PtoL_avg"] = PtoL_avg
            outputs["LtoP_avg"] = LtoP_avg
            lines.extend([
                "hbond ProtLig_PL \\",
                f"    donormask {receptor_mask} \\",
                f"    acceptormask {ligand_mask} \\",
                f"    avgout {PtoL_avg}",
                "hbond ProtLig_LP \\",
                f"    donormask {ligand_mask} \\",
                f"    acceptormask {receptor_mask} \\",
                f"    avgout {LtoP_avg}",
            ])

    # 3. Secondary Structure (Calculated on dry system in Pass 1)
    if cfg.ss.run:
        ss_sumout = f"ss_sumout_{name}.dat"
        ss_totalout = f"ss_totalout_{name}.dat"
        outputs["ss_sumout"] = ss_sumout
        outputs["ss_totalout"] = ss_totalout
        lines.append(f"secstruct sumout {ss_sumout} totalout {ss_totalout}")

    # 4. Cache Coordinates in Memory for PCA/Clustering
    if cfg.pca.run or cfg.cluster.run:
        lines.extend([
            f"reference {trajin} lastframe",
            "activeref 0",
            "autoimage",
            f"rms first {pca_cluster_mask}",
            "average crdset trajaverage",
            "createcrd trajectory"
        ])

    # ==========================================
    # EXECUTE PASS 1 (The only expensive disk read!)
    # ==========================================
    lines.append("run")

    # 5. Handle H-bond Datasets Post-processing (No disk reading required)
    if hb and (hb.pp or hb.bb or hb.pl):
        if hb.bb:
            BB_hbvtime = f"BB_hbvtime_{name}.dat"
            outputs["BB_hbvtime"] = BB_hbvtime
            lines.append(f"create {BB_hbvtime} BB_Prot[UU]")
        if hb.pl:
            PL_all_hbvtime = f"PL_all_hbvtime_{name}.dat"
            outputs["PL_all_hbvtime"] = PL_all_hbvtime
            lines.extend(["ProtLig_All = ProtLig_PL[UU] + ProtLig_LP[UU]", f"create {PL_all_hbvtime} ProtLig_All"])

    # 6. PCA (Executes on RAM-cached dataset)
    if cfg.pca.run:
        pca_out = f"pca_{name}.dat"
        outputs["pca_out"] = pca_out
        lines.extend([
            f"crdaction trajectory rms ref trajaverage {pca_cluster_mask}",
            f"crdaction trajectory matrix covar name covmatrix {pca_cluster_mask}",
            f"runanalysis diagmatrix covmatrix out evecs_{name}.dat vecs {n_eigen} name eigenvectors",
            f"crdaction trajectory projection modes eigenvectors beg 1 end {n_eigen} {pca_cluster_mask} out {pca_out}",
        ])

    # 7. Clustering (Executes on RAM-cached dataset)
    if cfg.cluster.run:
        cnumvtime = f"cnumvtime_{name}.dat"
        cpopvtime = f"cpopvtime_{name}.dat"
        csummary = f"csummary_{name}.dat"
        outputs["cnumvtime"] = cnumvtime
        outputs["cpopvtime"] = cpopvtime
        outputs["csummary"] = csummary
        lines.extend([
            "cluster c1 \\",
            f" kmeans clusters {n_clusters} randompoint maxit 500 \\",
            f" {pca_cluster_mask} \\",
            f" sieve 1 random \\",
            f" out {cnumvtime} \\",
            f" summary {csummary} \\",
            f" cpopvtime {cpopvtime} normframe \\",
            f" info cinfo_{name}.dat \\",
            f" repout crep_{name} repfmt pdb \\",
            f" avgout cavg_{name} avgfmt pdb",
        ])

    # ==========================================
    # EXECUTE PASS 2 (Pure RAM-speed operations)
    # ==========================================
    if cfg.pca.run or cfg.cluster.run or (hb and (hb.bb or hb.pl)):
        lines.append("run")

    lines.append("quit")
    cpptraj_input = "\n".join(lines)

    return cpptraj_input, outputs