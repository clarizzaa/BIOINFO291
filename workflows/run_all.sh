#!/usr/bin/env bash
# Reproduce the entire scRNA-seq immunotherapy analysis from a clean checkout.
#
#   conda env create -f environment/env-scrna.yml
#   conda activate scrna
#   bash workflows/run_all.sh
#
# Every step is independently runnable and declares its inputs and outputs at
# the top of the file. Step 00 downloads ~127 MB from GEO on the first run and
# is a no-op afterwards. Expect roughly three minutes end to end on a laptop,
# dominated by parsing the expression matrix in step 01.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "repository: $(pwd)"
echo "python:     $(python -c 'import sys; print(sys.version.split()[0])')"
echo "scanpy:     $(python -c 'import scanpy; print(scanpy.__version__)')"
echo "commit:     $(git rev-parse --short HEAD 2>/dev/null || echo 'not a git checkout')"
echo

for step in \
    00_download_data.py \
    01_build_anndata.py \
    02_qc.py \
    03_cluster.py \
    04_annotate.py \
    05_composition.py \
    06_pseudobulk_de.py \
    07_report.py
do
    echo "=============================================================="
    echo "workflows/${step}"
    echo "=============================================================="
    python "workflows/${step}"
    echo
done

echo "=============================================================="
echo "done. results/ figures/ reports/scrnaseq-immunotherapy.md are current."
