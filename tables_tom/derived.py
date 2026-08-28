"""Odvozene statistiky nad krizovou validaci — jeden vypocet pro vsechny tabulky.

Table 3 (hlavni text), Table S1 (vsech 24 kombinaci) i poznamky pod nimi
stoji na tychz cislech. Pocitaji se tedy jednou tady, ne v kazdem generatoru
zvlast, aby se nemohly rozejit.

Permutacni p-hodnota se pocita z testovaci statistiky = **prumer AUC pres
5 foldu** (ne median, ktery je ve sloupci AUC) jako p = (b + 1) / (m + 1)
s m = 100 permutacemi; nejmensi dosazitelna hodnota je proto 0,0099.
Benjamini-Hochberg bezi pres vsech 24 kombinaci vcetne voxelovych — tak,
jak to popisuje poznamka pod tabulkou 3. Tataz statistika se pocita i pro
accuracy (`p_acc`, `q_acc`), aby se tvrzeni "pro accuracy neprezije korekci
zadna kombinace" dalo doopravdy overit, ne jen prevzit.
"""

from __future__ import annotations

import collections
import statistics as st

import common


class ComboStats(collections.namedtuple(
        "ComboStats",
        "fset method auc acc n_features auc_median auc_q1 auc_q3 auc_mean "
        "acc_median n_median null_mean null_std kappa p q p_acc q_acc")):
    """Vsechno, co kterakoli tabulka o jedne kombinaci potrebuje."""


def cv_statistics():
    """{(f_set_type, method): ComboStats} pro vsech 24 kombinaci."""
    cv = common.load_cv()
    null_summary = common.load_null_summary()
    null_iters = common.load_null_per_iteration()
    null_iters_acc = common.load_null_per_iteration("ACC")

    keys = list(common.combos())
    missing = [k for k in keys if k not in cv]
    if missing:
        raise SystemExit(f"ve vysledcich chybi kombinace: {missing}")

    raw = {}
    for key in keys:
        folds = [cv[key][s] for s in range(common.N_SPLITS)]
        auc = [f.auc for f in folds]
        acc = [f.acc for f in folds]
        nfe = [f.n_features for f in folds]
        q1, med, q3 = common.quartiles(auc)
        null_mean, null_std = null_summary[key]
        raw[key] = dict(
            fset=key[0], method=key[1], auc=auc, acc=acc, n_features=nfe,
            auc_median=med, auc_q1=q1, auc_q3=q3, auc_mean=st.mean(auc),
            acc_median=st.median(acc), n_median=st.median(nfe),
            null_mean=null_mean, null_std=null_std,
            kappa=common.kappa_index(st.mean(auc), null_mean),
            p=common.permutation_p(st.mean(auc), null_iters[key]),
            p_acc=common.permutation_p(st.mean(acc), null_iters_acc[key]),
        )

    qvals = common.benjamini_hochberg([raw[k]["p"] for k in keys])
    qvals_acc = common.benjamini_hochberg([raw[k]["p_acc"] for k in keys])
    return {k: ComboStats(q=qv, q_acc=qa, **raw[k])
            for k, qv, qa in zip(keys, qvals, qvals_acc)}


def pooled_best(stats, pool):
    """Sloucene AUC pres foldy vybranych kombinaci (Table 5, prvni radek)."""
    values = [x for key in pool for x in stats[key].auc]
    return values


def nb_correction():
    """(k, n_test, n_train, korekce, nafouknuti SE, df) z velikosti foldu v datech."""
    import math

    import common

    labels = common.load_fold_labels()
    k = len(labels)
    n_test = st.mean(len(v) for v in labels.values())
    n_train = st.mean(sum(len(w) for s, w in labels.items() if s != split)
                      for split in labels)
    correction = 1 / k + n_test / n_train
    return dict(k=k, n_test=n_test, n_train=n_train, correction=correction,
                se_inflation=math.sqrt(correction * k), df=k - 1)


def nb_statistic(a_values, b_values, correction):
    """(prumerny rozdil, t bez korekce, t s korekci) pro jednu dvojici."""
    import math

    diff = [x - y for x, y in zip(a_values, b_values)]
    mean, var = st.mean(diff), st.variance(diff)
    return (mean,
            mean / math.sqrt(var / len(diff)),
            mean / math.sqrt(correction * var))


def nadeau_bengio(stats, fset, metric="auc"):
    """Korigovany resampled t-test pro vsechny pary pipeline v jednom datasetu.

    Nadeau & Bengio (2003): rozdily pres foldy k-fold CV jsou zavisle, protoze
    treninkove mnoziny se prekryvaji, takze naivni parovy t-test podcenuje
    rozptyl. Korekce nafoukne rozptyl faktorem

        1/k + n_test/n_train

    Velikosti mnozin se berou z dat (prumer pres foldy), ne z hlavy: pri
    5-fold CV nad 141 pacienty vychazi n_test/n_train = 28,2/112,8 = 0,25
    a korekce presne 0,45, tedy nafouknuti smerodatne chyby 1,50x.
    Stupne volnosti zustavaji k-1.

    Vraci (metadata, [(A, B, rozdil, t_naive, t_NB)]) v poradi dvojic.
    """
    import itertools

    import common

    meta = nb_correction()
    pairs = []
    for a, b in itertools.combinations(common.METHODS, 2):
        va = getattr(stats[(fset, a)], metric)
        vb = getattr(stats[(fset, b)], metric)
        pairs.append((a, b) + nb_statistic(va, vb, meta["correction"]))
    return meta, pairs
