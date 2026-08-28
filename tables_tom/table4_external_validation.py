"""Table 4 — externi validace na MR CLEAN Registry.

Radky `split == "all_fold"` tehoz CSV jsou jediny beh kazdeho modelu na
Registry; voxelove sady tam radek nemaji vubec, takze tabulka ma 16 radku.
Delta se pocita z neredukovanych hodnot (Registry AUC minus CV median AUC),
ne z cisel zaokrouhlenych na tri desetinna mista.
"""

import statistics as st

import common
import derived

TITLE = "External validation in the MR CLEAN Registry cohort"

NAME = "table4_external_validation.tex"

LABEL = "tab:external-validation"

#: Prah, od ktereho se kombinace povazuje za takovou, ktera v CV diskriminovala.
#: Osm kombinaci nad 0,500 zahrnuje i dve centerline tesne nad nahodou; teprve
#: 0,600 vybere tech sest, u kterych ma srovnani s Registry smysl.
DISCRIMINATED = 0.6

SOURCES = [common.RESULTS_CSV.name]

CAPTION = (
    "External validation in the MR CLEAN Registry cohort. "
    "Each pipeline was refitted on all {n_patients} development patients with "
    "its tuned hyperparameters and applied once to the Registry cohort. "
    r"CV, cross-validated median over the five outer folds of the same "
    r"combination in Table~\ref{{tab:cv-performance}}; Reg., Registry; "
    r"ACC, accuracy; $\Delta$AUC, Registry AUC minus cross-validated median "
    "AUC, a negative value being a loss of discrimination on transfer; "
    r"other abbreviations as in Table~\ref{{tab:cv-performance}}. "
    "The voxel-based datasets were not transferred externally and therefore "
    "have no row here, which is why the table has {n_models} rows rather than 24."
)

NOTE = r"""
Across the {n_models} models the Registry AUC ranged from {auc_lo} to {auc_hi} with a median of {auc_med}, and {n_above_half} of them exceeded 0.50.
Registry accuracy ranged from {acc_lo} to {acc_hi} with a median of {acc_med}, and no model reached the majority-class accuracy of the development cohort, {baseline}.
The sign of $\Delta$ follows the cross-validated value and nothing else: the {n_high} combinations whose cross-validated median AUC was above 0.500 all moved downwards on transfer, by {high_hi} to {high_lo}, and the {n_low} that were at or below it all moved upwards, by {low_lo} to {low_hi}.
The upward movement is therefore a regression to chance of models that had performed below chance internally, not a gain in generalization, and it must not be presented as one.
The only combinations for which the comparison is informative are the {n_informative} that discriminated in cross-validation, that is reached a cross-validated median AUC of at least {threshold}; all of them lose between {loss_lo} and {loss_hi} of AUC.
\NOTEWARN{{$n$ Registry is not stated in the results files and is not the same for every model. Reconstructing the smallest denominator compatible with the decimal expansion of each reported accuracy leaves exactly three cohort sizes: 1649 for eight models, 1760 for six and 1761 for two. Neither the 1906 of the exclusion cascade nor the 1839 identifiers stored with the cohort is compatible with any of the sixteen. Until this is resolved the AUC values in this table are not strictly comparable with one another}}
"""


SELECTOR = {"rf_lasso": "LASSO", "rf_rfi": "RFI",
            "svc_lasso": r"$\ell_1$ emb.", "svc_rfi": "RFI"}
CLASSIFIER = {"rf_lasso": "XGBRF", "rf_rfi": "XGBRF",
              "svc_lasso": "LinearSVC", "svc_rfi": "NuSVC"}


def render(stats=None):
    common.set_table("Tabulka 4")
    stats = stats or derived.cv_statistics()
    external = common.load_external()

    groups = []
    for fset in common.PATIENT_FSETS:
        fname, roi = common.FSETS[fset]
        rows = []
        for method in common.METHODS:
            s = stats[(fset, method)]
            ext = external[(fset, method)]
            rows.append([
                fname, roi, SELECTOR[method], CLASSIFIER[method],
                common.f3(s.auc_median),
                common.f3(s.acc_median),
                common.f3(ext.auc),
                common.f3(ext.acc),
                common.signed(ext.auc - s.auc_median),
            ])
        groups.append(rows)

    missing = [k for k in common.combos(["voxel", "voxel_skeleton"]) if k in external]
    if missing:
        raise SystemExit(f"voxelove sady maji Registry radek: {missing}")

    header = [
        ["Feature set", "ROI", "Selector", "Classifier", "CV", "CV", "Reg.",
         "Reg.", r"$\Delta$"],
        ["", "", "", "", "AUC", "ACC", "AUC", "ACC", "AUC"],
    ]
    style = [r"\footnotesize", r"\setlength{\tabcolsep}{3pt}"]
    body = common.tabular("llllrrrrr", header, common.align(groups), style)

    return body, facts(stats, external)


def facts(stats, external):
    """Cisla do popisku a poznamky, dopoctena z tychz radku jako telo tabulky."""
    labels = common.load_fold_labels()
    n_patients = sum(len(v) for v in labels.values())
    baseline = sum(sum(v) for v in labels.values()) / n_patients

    keys = list(external)
    auc = [external[k].auc for k in keys]
    acc = [external[k].acc for k in keys]
    delta = {k: external[k].auc - stats[k].auc_median for k in keys}
    high = [k for k in keys if stats[k].auc_median > 0.5]
    low = [k for k in keys if stats[k].auc_median <= 0.5]
    # Tvrzeni poznamky: smer posunu na Registry sleduje vyhradne CV hodnotu.
    # Kdyby to prestalo platit, musi skript spadnout, ne to tise vysadit.
    if not (all(delta[k] < 0 for k in high) and all(delta[k] >= 0 for k in low)):
        raise SystemExit("smer posunu uz nesleduje CV medi\u00e1n -- prepsat poznamku")
    informative = [k for k in keys if stats[k].auc_median >= DISCRIMINATED]

    return dict(
        n_patients=n_patients, n_models=len(keys),
        auc_lo=common.f3(min(auc)), auc_hi=common.f3(max(auc)),
        auc_med=common.f3(st.median(auc)),
        n_above_half=sum(1 for a in auc if a > 0.5),
        acc_lo=common.f3(min(acc)), acc_hi=common.f3(max(acc)),
        acc_med=common.f3(st.median(acc)), baseline=common.f3(baseline),
        n_high=len(high), n_low=len(low),
        high_hi=common.f3m(max(delta[k] for k in high)),
        high_lo=common.f3m(min(delta[k] for k in high)),
        low_lo=common.f3m(min(delta[k] for k in low)),
        low_hi=common.f3m(max(delta[k] for k in low)),
        n_informative=len(informative), threshold=common.f3(DISCRIMINATED),
        loss_lo=common.f3(min(-delta[k] for k in informative)),
        loss_hi=common.f3(max(-delta[k] for k in informative)),
    )

if __name__ == "__main__":
    print(common.write(NAME, render()[0], __file__, SOURCES))
