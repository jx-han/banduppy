"""Kagome (2x2x1 SC) -> (1x1x1 PC) band unfolding tutorial script.

This script is designed for the input files in tutorials/QuantumEspresso/kagome.
It focuses on the beginner workflow:
1) (recommended) generate SC k-points from primitive-cell path,
   or (convenience) reuse an existing SC K_POINTS block,
2) run QE scf/bands (optional, controlled by flags),
3) read wavefunctions with banduppy,
4) unfold and plot.
"""

from __future__ import annotations

import shutil
from pathlib import Path
import sys
from subprocess import run

import banduppy
import numpy as np

# ----------------------------- User settings ---------------------------------
# Convenience mode: reuse existing SC K_POINTS from band.in for QE run input.
# NOTE: this mode is not the primary workflow in docs/USAGE.md for defining a PC path.
# Recommended for reproducible PC high-symmetry unfolding: set to False and generate from PC path.
USE_EXISTING_SC_KPOINTS = True

# Quick mode:
#   python run_banduppy_qe_kagome.py --run-all   -> generate kpts + run QE + unfold + plot
#   python run_banduppy_qe_kagome.py             -> default: no QE run, only read/unfold/plot
AUTO_RUN_ALL = "--run-all" in sys.argv

RUN_QE_SCF = AUTO_RUN_ALL
RUN_QE_BANDS = AUTO_RUN_ALL
READ_WAVEFUNCTION = True
DO_UNFOLD = True
DO_PLOT = True

# Set your QE executable command, e.g. ["pw.x"] or ["mpirun", "-np", "16", "pw.x"]
QE_EXE = ["pw.x"]

# Supercell used by kagome input (2x2x1)
SUPER_CELL = [[2, 0, 0], [0, 2, 0], [0, 0, 1]]

# Primitive-cell high symmetry path: Gamma -> K -> M -> Gamma
PC_BZ_PATH = [
    [0.0, 0.0, 0.0],
    [1 / 3, 1 / 3, 0.0],
    [1 / 2, 0.0, 0.0],
    [0.0, 0.0, 0.0],
]
NPOINTS_PER_SEG = (40, 40, 40)
SPECIAL_K_LABELS = [r"$\Gamma$", "K", "M", r"$\Gamma$"]

# Plot window
E_FERMI = 0.0
E_MIN = -3.0
E_MAX = 3.0

# ----------------------------- Paths -----------------------------------------
THIS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = THIS_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SCF_TEMPLATE = THIS_DIR / "scf.in"
BANDS_TEMPLATE = THIS_DIR / "band.in"
SCF_RUN_INPUT = THIS_DIR / "scf_run.in"
BANDS_RUN_INPUT = THIS_DIR / "band_run.in"

print(f"BandUPpy version: {banduppy.__version__}")

# --------------------- Step 1: Prepare SC k-points ---------------------------
unfold = banduppy.Unfolding(supercell=SUPER_CELL, print_log="high")

if USE_EXISTING_SC_KPOINTS:
    # Use K_POINTS block directly from your provided supercell input: band.in
    with open(BANDS_TEMPLATE, "r", encoding="utf-8") as f:
        band_in_text = f.read()
    if "K_POINTS" not in band_in_text:
        raise RuntimeError("No K_POINTS block found in band.in")
    kpoints_sc = "K_POINTS" + band_in_text.split("K_POINTS", maxsplit=1)[1]
    special_kpoints_pos_labels = None
    print("[WARN] Reusing SC K_POINTS from band.in. PC-path labels may not be strictly mapped.")
else:
    # Optional route: build SC k-points by mapping a PC path through supercell matrix
    (
        _kpointsPBZ_full,
        _kpointsPBZ_unique,
        _kpointsSBZ,
        _mapping,
        special_kpoints_pos_labels,
    ) = unfold.generate_SC_Kpts_from_pc_k_path(
        pathPBZ=PC_BZ_PATH,
        nk=NPOINTS_PER_SEG,
        labels=SPECIAL_K_LABELS,
        kpts_weights=1,
        save_all_kpts=True,
        save_sc_kpts=True,
        save_dir=str(THIS_DIR),
        file_name_suffix="_kagome",
        file_format="qe",
    )
    with open(THIS_DIR / "KPOINTS_SC_kagome", "r", encoding="utf-8") as f:
        kpoints_sc = "".join(
            line for line in f.readlines() if not line.lstrip().startswith("!")
        )

# ------------------ Step 2: Build QE run input files -------------------------

if RUN_QE_SCF:
    # SCF file already has automatic mesh. We keep it unchanged except copy.
    shutil.copy(SCF_TEMPLATE, SCF_RUN_INPUT)
    run(QE_EXE + ["-input", str(SCF_RUN_INPUT)], check=True, cwd=THIS_DIR)

if RUN_QE_BANDS:
    with open(BANDS_TEMPLATE, "r", encoding="utf-8") as f:
        band_in_text = f.read()
    with open(BANDS_RUN_INPUT, "w", encoding="utf-8") as f:
        # Replace the existing K_POINTS block with selected SC path block.
        f.write(band_in_text.split("K_POINTS", maxsplit=1)[0])
        f.write(kpoints_sc)
    run(QE_EXE + ["-input", str(BANDS_RUN_INPUT)], check=True, cwd=THIS_DIR)

# ------------------ Step 3: Read wavefunction and unfold ---------------------
if not AUTO_RUN_ALL:
    print("Tip: add --run-all to let this script run QE automatically.")

if READ_WAVEFUNCTION:
    # NOTE:
    # 1) Ensure "prefix" is explicitly set in QE input.
    # 2) BandStructure(code="espresso") expects files in <prefix>.save.
    # Example: prefix='kagome_221' -> kagome_221.save
    PREFIX = str(THIS_DIR / "kagome_221")
    bands = banduppy.BandStructure(code="espresso", spinor=False, prefix=PREFIX)
else:
    raise RuntimeError("READ_WAVEFUNCTION=False is not supported in this tutorial script.")

if DO_UNFOLD:
    unfolded_bandstructure, kpline = unfold.Unfold(
        bands,
        kline_discontinuity_threshold=0.1,
        save_unfolded_kpts={
            "save2file": True,
            "fdir": str(RESULTS_DIR),
            "fname": "kpoints_unfolded_kagome",
            "fname_suffix": "",
        },
        save_unfolded_bandstr={
            "save2file": True,
            "fdir": str(RESULTS_DIR),
            "fname": "bandstructure_unfolded_kagome",
            "fname_suffix": "",
        },
    )
else:
    unfolded_bandstructure = np.loadtxt(
        RESULTS_DIR / "bandstructure_unfolded_kagome.dat"
    )
    kpline = np.loadtxt(RESULTS_DIR / "kpoints_unfolded_kagome.dat")[:, 1]

if DO_PLOT:
    plotter = banduppy.Plotting(save_figure_dir=str(RESULTS_DIR))
    plotter.plot_ebs(
        kpath_in_angs=kpline,
        unfolded_bandstructure=unfolded_bandstructure,
        save_file_name="unfolded_bandstructure_kagome.png",
        CountFig=None,
        Ef=E_FERMI,
        Emin=E_MIN,
        Emax=E_MAX,
        pad_energy_scale=0.5,
        mode="fatband",
        special_kpoints=special_kpoints_pos_labels,
        plotSC=True,
        fatfactor=18,
        nE=400,
        smear=0.06,
        color="red",
        color_map="viridis",
        show_colorbar=True,
    )

print("Done: Kagome unfolding workflow finished.")
