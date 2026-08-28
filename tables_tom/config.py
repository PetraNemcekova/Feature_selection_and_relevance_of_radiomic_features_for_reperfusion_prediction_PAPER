"""Jedine misto, kde se neco nastavuje: kde lezi stazena data.

Vychozi hodnota je `data/` v korenu tohohle repozitare. Na jinem stroji staci
prepsat DATA_DIR nize, nebo pustit generovani s promennou prostredi:

    DATA_DIR=/jina/cesta/k/datum python3 make_all.py

Ocekavana struktura uvnitr DATA_DIR (tak, jak ji vyrobi skripty v `scripts/`):

    gdrive/Models_comparicon/final_test_results_all_folds_updated.csv
    gdrive/Models_comparicon/final_random_test_results.csv
    gdrive/Models_comparicon/final_random_test_results_summary.csv
    gdrive/Models_comparicon/henks_icc_test_results_all_folds.csv
    gdrive/Boosting/Boosting_results/overall_metrics_summary.csv
    gdrive/Boosting/Predictions/*_patient_results.csv
    onedrive/results_Henks_pipeline/03_feature_selection/icc_selection_report.csv
    onedrive/results_Henks_pipeline/07_split_cv/
    heterogeneity/                      (read-only git klon, vetev public_branch)
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

DATA_DIR = Path(os.environ.get("DATA_DIR", HERE.parent / "data"))

#: Kam se ukladaji vygenerovane tabulky (.txt k vlozeni do LaTeXu).
OUTPUT_DIR = HERE / "output"
