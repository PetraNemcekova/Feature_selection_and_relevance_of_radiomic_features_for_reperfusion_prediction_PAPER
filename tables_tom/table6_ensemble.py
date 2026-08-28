"""Tabulka 6 — patnact konfiguraci diskretniho AdaBoostu proti svym clenum.

Prumerna accuracy ensemblu je z `Boosting_results/overall_metrics_summary.csv`
(15 konfiguraci x 5 foldu = 75 modelu). Nejlepsi slaby klasifikator se hleda
v tomtez zdroji jako zbytek clanku, tedy ve `final_test_results_all_folds_updated.csv`:
je to kombinace s nejvyssi prumernou accuracy pres 5 foldu z tech, ktere maji
v poolu dane konfigurace svuj dataset.

Slozeni poolu je zakodovane v nazvu konfigurace a rozebira ho `pool_of()`;
voxelove sady v zadnem poolu nejsou, protoze jejich predikce jsou po voxelech.
"""

import statistics as st

import common

TITLE = "Ensemble analysis: fifteen AdaBoost configurations against their members"

NAME = "table6_ensemble.tex"

LABEL = "tab:ensemble"

SOURCES = ["Boosting_results/overall_metrics_summary.csv", common.RESULTS_CSV.name]

CAPTION = (
    "Ensemble analysis: the {n_configs} configurations of discrete, that is "
    r"binary, AdaBoost \cite{{Freund1997}} applied to the stored prediction "
    "vectors of the "
    "{n_weak} patient-level weak classifiers (four patient-level datasets "
    r"$\times$ four pipelines). "
    "Each configuration was fitted on the five outer folds, giving {n_models} "
    "ensemble models. "
    r"ACC $\varnothing$, mean accuracy of the configuration across the five "
    "folds; best weak classifier, the single pipeline in the configuration's "
    r"pool with the highest mean accuracy, and its value; $\Delta$, the mean "
    "accuracy of the ensemble minus that of the best weak classifier. "
    r"A negative $\Delta$ means the ensemble is worse than the best model it "
    "combines. "
    "The configuration name states which of the four patient-level datasets "
    "form its pool, each contributing all four pipelines: "
    r"\texttt{{type1}} pools all four datasets (16 weak classifiers), "
    r"\texttt{{type2}} a whole-thrombus dataset with its own centerline "
    r"counterpart (8), \texttt{{type3}} a single dataset (4), \texttt{{type4}} "
    r"two datasets that are not such a pair (8) and \texttt{{type5}} all "
    "datasets but one (12). "
    r"\texttt{{distrib.}}\ abbreviates the distribution-based dataset and "
    r"\emph{{cent.}} the centerline region of interest, as in "
    r"Table~\ref{{tab:cv-performance}}. "
    "The two voxel-based datasets were excluded from every pool because their "
    "predictions are defined per voxel."
)

NOTE = r"""
$\Delta$ is negative for all {n_configs} configurations, between {delta_hi} and {delta_lo}; no ensemble outperformed the best single pipeline in its own pool.
The worst result belongs to {worst_config}, the configuration that pools all feature sets.
Across all {n_models} fitted ensemble models accuracy averages ${acc_mean} \pm {acc_sd}$ with a range of {acc_lo}--{acc_hi}.
The mechanism is documented by the fitted weights: in the all-feature-set configuration, {n_negative} of the {n_rounds} boosting rounds ({n_weak} rounds $\times$ five folds) received a negative weight $\alpha$, meaning that the weak classifier admitted in that round performed worse than chance on the reweighted data.
The individual pipelines therefore do not make complementary errors, and the boosting assumption of weak classifiers reliably better than chance is not met.
Labels were coded as $\{{-1,+1\}}$, the weight of a round was $\alpha = \tfrac{{1}}{{2}}\ln\frac{{1-\varepsilon}}{{\varepsilon}}$ with $\varepsilon$ the error of the admitted classifier on the currently reweighted data, and each weak classifier could be admitted at most once, so a pool of $k$ members yields at most $k$ rounds.
The weak classifiers were not retrained: the procedure is applied to models that had already been fitted, which makes it methodologically a form of stacking rather than boosting proper.
The best weak classifier of {same_pool_a} and of {same_pool_b} is the same pipeline, because the pool of the latter contains the pool of the former.
"""


FSET_LABEL = {
    "global": "global",
    "global_skeleton": "global cent.",
    "distribution": "distrib.",
    "distribution_skeleton": r"distrib.\ cent.",
}

METHOD_LABEL = {m: f"{sel}--{clf}" for m, (sel, clf) in common.METHODS.items()}


def pool_of(config):
    """Datasety, jejichz ctyri pipeline tvori pool dane konfigurace."""
    every = list(common.PATIENT_FSETS)
    if config == "type1_all_featuresets":
        return every
    if config.startswith("type2_") and config.endswith("_pair"):
        base = config[len("type2_"):-len("_pair")]
        return [base, f"{base}_skeleton"]
    if config.startswith("type3_"):
        return [config[len("type3_"):]]
    if config.startswith("type4_"):
        return config[len("type4_"):].split("__")
    if config.startswith("type5_all_but_"):
        excluded = config[len("type5_all_but_"):]
        return [f for f in every if f != excluded]
    raise SystemExit(f"neznamy tvar nazvu konfigurace: {config}")


def texttt(name):
    return r"\texttt{" + name.replace("_", r"\_\allowbreak ") + "}"


def render(stats=None):
    common.set_table("Tabulka 6")
    cv = common.load_cv()
    boosted = common.load_boosting_accuracy()

    weak_mean = {key: st.mean(f.acc for f in folds.values())
                 for key, folds in cv.items()}

    deltas = {}
    groups, current, rows = [], None, []
    for config in sorted(boosted):
        pool = pool_of(config)
        unknown = [f for f in pool if f not in common.PATIENT_FSETS]
        if unknown:
            raise SystemExit(f"{config}: pool obsahuje {unknown}")

        best = max(common.combos(pool), key=lambda k: weak_mean[k])
        ensemble = st.mean(boosted[config])

        family = config.split("_", 1)[0]
        if family != current:
            if rows:
                groups.append(rows)
            rows, current = [], family
        deltas[config] = ensemble - weak_mean[best]
        rows.append([
            texttt(config),
            common.f4(ensemble),
            f"{FSET_LABEL[best[0]]}/{METHOD_LABEL[best[1]]}",
            common.f4(weak_mean[best]),
            common.signed(ensemble - weak_mean[best]),
        ])
    groups.append(rows)

    colspec = (r">{\raggedright\arraybackslash}p{0.25\textwidth}r"
               r">{\raggedright\arraybackslash}p{0.30\textwidth}rr")
    header = [["Configuration", r"ACC $\varnothing$", "Best weak classifier",
               r"Its ACC $\varnothing$", r"$\Delta$"]]
    style = [r"\scriptsize", r"\setlength{\tabcolsep}{3pt}"]
    body = common.tabular(colspec, header, common.align(groups), style)

    return body, facts(boosted, weak_mean, deltas)


def facts(boosted, weak_mean, deltas):
    """Cisla do popisku a poznamky, dopoctena z tychz zdroju jako telo tabulky."""
    every = [st.mean(v) for v in boosted.values()]
    per_model = [a for v in boosted.values() for a in v]
    alpha = common.load_boosting_alpha()
    worst = min(deltas, key=deltas.get)
    n_weak = len(common.PATIENT_FSETS) * len(common.METHODS)

    if any(d >= 0 for d in deltas.values()):
        raise SystemExit("nektera konfigurace uz sveho nejlepsiho clena "
                         "prekonava -- prepsat poznamku")

    return dict(
        n_configs=len(boosted), n_weak=n_weak,
        n_models=len(boosted) * common.N_SPLITS,
        delta_lo=common.f3m(min(deltas.values())),
        delta_hi=common.f3m(max(deltas.values())),
        worst_config=texttt(worst),
        acc_mean=common.f3(st.mean(per_model)),
        acc_sd=common.f3(st.stdev(per_model)),
        acc_lo=common.f3(min(per_model)), acc_hi=common.f3(max(per_model)),
        n_rounds=len(alpha), n_negative=sum(1 for a in alpha if a < 0),
        same_pool_a=texttt("type3_global"),
        same_pool_b=texttt("type1_all_featuresets"),
    )

if __name__ == "__main__":
    print(common.write(NAME, render()[0], __file__, SOURCES))
