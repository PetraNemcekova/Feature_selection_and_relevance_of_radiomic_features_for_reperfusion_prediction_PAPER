"""Tabulka 1 — vyber pacientu v obou kohortach.

POZOR: tohle je jedina tabulka, jejiz vetsina NENI ve stazenych datech.
Vylucovaci kaskada existuje jen v rukopisu; ve zdrojich k ni neni ani soubor,
ani kod. Cisla proto prochazi pres `common.manual()` a `make_all.py` je vypise
do PROVENANCE.md, aby bylo videt, co je odkud.

Z dat se overuje to, co overit jde:
  - konecna kohorta 141 pacientu a pocet pozitivnich se pocita z ulozenych
    popisku vnejsich foldu,
  - pocet ulozenych Registry ID z `Registry_data_IDs.json`,
  - soucty kaskady musi sedet na deklarovane koncove stavy, jinak skript spadne.

Rozpor u velikosti Registry (1906 z kaskady / 1839 ulozenych ID / 1649, 1760
a 1761 zpetne rekonstruovanych z desetinneho rozvoje externich accuracy)
zustava neuzavreny -- viz OTAZKY B2. Skript ho hlasi, neresi.

Popisek i poznamka jsou prevzate z `paper/sections/06_tables.tex`.
"""

import common

TITLE = "Patient selection in the two cohorts"

NAME = "table1_cohorts.tex"

LABEL = "tab:cohorts"

SOURCES = ["Boosting/Predictions/*_patient_results.csv (popisky foldu)",
           "heterogeneity/Registry_data_IDs.json", "rukopis (vylucovaci kaskada)"]

#: Vylucovaci kaskada tak, jak ji uvadi rukopis. Nedohledatelne ve zdrojich.
NOIV_INITIAL = 539
NOIV_EXTRACTION_FAILURE = 243
NOIV_MANUAL_REVIEW = 155

REGISTRY_INITIAL = 2597
REGISTRY_MISSING_ETICI = 16
REGISTRY_MISSING_SEGMENTATION = 575
REGISTRY_SPACING = 100

#: Velikosti externi kohorty zpetne rekonstruovane z desetinneho rozvoje
#: externich accuracy: {n: pocet modelu}. Viz poznamka pod tabulkou 4.
REGISTRY_RECONSTRUCTED = {1649: 8, 1760: 6, 1761: 2}

DASH = "---"

CAPTION = (
    "Patient selection in the two cohorts. "
    "MR CLEAN NO-IV was used for model development and cross-validation, "
    "the MR CLEAN Registry as the independent external cohort. "
    "Entries are numbers of patients; an em dash marks an exclusion step that "
    "does not apply to that cohort. "
    "eTICI, expanded Thrombolysis in Cerebral Infarction score; the outcome "
    "modeled throughout this article is near-complete or complete reperfusion, "
    "defined as a final eTICI score of 2C or 3. "
    "Slice spacing refers to the through-plane spacing of the non-contrast CT "
    "acquisition."
)

NOTE = r"""
The manual review of segmentation quality was carried out on the MR CLEAN NO-IV cohort only.
No segmentation was reviewed or rejected in the MR CLEAN Registry cohort, so the two cohorts differ in segmentation quality control as well as in population.
This is a property of the design and is the single largest asymmetry between the development and the external cohort.
The review was blinded to the eTICI score: it judged the quality and the anatomical placement of the segmentation only, so the {n_review} exclusions it produced cannot have been informed by the outcome.
Of the {n_noiv} patients that remain, {n_positive} ({pct}\%) reached eTICI 2C--3; the proportion varies across the five outer folds ({ratios}), so in the first fold the majority class is the absence rather than the presence of near-complete or complete reperfusion.
\NOTETODO{{breakdown of how many of the {n_review} reviewed cases were rejected by which criterion}}
\NOTETODO{{number and proportion of patients with eTICI 2C--3 reperfusion in the Registry cohort, which the table leaves as an em dash}}
\NOTEWARN{{size of the Registry cohort: the exclusion cascade gives {n_registry}, the stored identifier list holds {n_ids}, and the denominators reconstructed from the decimal expansion of the reported external accuracies are {reconstructed}. Neither {n_registry} nor {n_ids} is compatible with any of the sixteen transferred models, and the reconstructed values are mutually incompatible, so the external cohort is not the same across feature sets}}
"""


def render(stats=None):
    common.set_table("Tabulka 1")

    labels = common.load_fold_labels()
    n_noiv = sum(len(v) for v in labels.values())
    n_positive = sum(sum(v) for v in labels.values())
    n_registry_ids = len(common.load_registry_ids())

    for value, why in [
        (NOIV_INITIAL, "MR CLEAN NO-IV, vychozi kohorta"),
        (NOIV_EXTRACTION_FAILURE, "NO-IV, vyrazeno pri extrakci priznaku"),
        (NOIV_MANUAL_REVIEW, "NO-IV, vyrazeno rucni kontrolou segmentaci"),
        (REGISTRY_INITIAL, "MR CLEAN Registry, vychozi kohorta"),
        (REGISTRY_MISSING_ETICI, "Registry, chybi eTICI"),
        (REGISTRY_MISSING_SEGMENTATION, "Registry, chybi segmentace"),
        (REGISTRY_SPACING, "Registry, spacing rezu > 1 mm"),
    ]:
        common.manual(value, why + " (jen z rukopisu, ve zdrojich neni)")

    derived_noiv = NOIV_INITIAL - NOIV_EXTRACTION_FAILURE - NOIV_MANUAL_REVIEW
    if derived_noiv != n_noiv:
        raise SystemExit(
            f"kaskada NO-IV dava {derived_noiv}, ale ulozene foldy maji {n_noiv}")

    n_registry = (REGISTRY_INITIAL - REGISTRY_MISSING_ETICI
                  - REGISTRY_MISSING_SEGMENTATION - REGISTRY_SPACING)
    common.manual(
        f"{n_registry} z kaskady vs. {n_registry_ids} ulozenych ID vs. "
        + "/".join(str(n) for n in REGISTRY_RECONSTRUCTED)
        + " rekonstruovanych z externich accuracy",
        "velikost Registry neni v datech jednoznacna (OTAZKY B2)")

    pct = 100 * n_positive / n_noiv
    todo = common.manual(
        DASH, "podil eTICI 2C-3 v Registry -- ve zdrojich neni")

    groups = [
        [["Initial cohort", str(NOIV_INITIAL), str(REGISTRY_INITIAL)]],
        [
            [r"\multicolumn{3}{l}{\emph{Excluded}}"],
            [r"\quad Missing eTICI score", DASH, str(REGISTRY_MISSING_ETICI)],
            [r"\quad Missing thrombus segmentation", DASH,
             str(REGISTRY_MISSING_SEGMENTATION)],
            [r"\quad Slice spacing $>$ 1~mm", DASH, str(REGISTRY_SPACING)],
            [r"\quad Feature extraction failure", str(NOIV_EXTRACTION_FAILURE), DASH],
            [r"\quad Manual segmentation quality review",
             str(NOIV_MANUAL_REVIEW), r"\emph{not performed}"],
        ],
        [
            ["Final analysis cohort", rf"\textbf{{{n_noiv}}}",
             rf"\textbf{{{n_registry}}}"],
            [r"Reperfusion eTICI 2C--3, $n$ (\%)",
             f"{n_positive} ({pct:.1f}\\%)", todo],
        ],
    ]

    header = [["Step", "MR CLEAN NO-IV", "MR CLEAN Registry"]]
    style = [r"\footnotesize", r"\setlength{\tabcolsep}{4pt}"]
    body = common.tabular("lrr", header, groups, style)

    ratios = ", ".join(common.f3(sum(labels[s]) / len(labels[s]))
                       for s in sorted(labels))
    reconstructed = ", ".join(
        f"{n} ({m} models)" for n, m in sorted(REGISTRY_RECONSTRUCTED.items()))
    numbers = dict(
        n_review=NOIV_MANUAL_REVIEW, n_noiv=n_noiv, n_positive=n_positive,
        pct=f"{pct:.1f}", ratios=ratios, n_registry=n_registry,
        n_ids=n_registry_ids, reconstructed=reconstructed)
    return body, numbers


if __name__ == "__main__":
    print(common.write(NAME, render()[0], __file__, SOURCES))
