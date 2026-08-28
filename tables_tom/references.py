"""Bibliograficke zaznamy, ktere supplement cituje.

Zamerne tady, ne ctenim z `paper/BibFile.bib`. `paper/` je pracovni kopie,
ktera se s Overleafem rozchazi -- pri posledni kontrole mel Overleaf 17 zaznamu
a `paper/` 70 -- takze cist odtud znamena vyrabet supplement z necheho, co se
nikde nereprodukuje. Zaznamy nize jsou soucasti supplementu a `make_all.py`
z nich sklada `output/BibFile.bib`.

Kdyz do popisku pribude citace, musi sem pribyt i zaznam; jinak generovani
spadne. Poradi klicu tady nerozhoduje, sazi se v poradi citovani.
"""

#: cite klic -> cely BibTeXovy zaznam
ENTRIES = {
    "vanVoorst2022": r"""
@article{vanVoorst2022,
  doi = {10.1136/jnis-2022-019085},
  url = {https://doi.org/10.1136/jnis-2022-019085},
  year = {2022},
  month = jul,
  publisher = {{BMJ}},
  pages = {neurintsurg--2022--019085},
  author = {Henk van Voorst and Agnetha A E Bruggeman and Wenjin Yang and Jurr Andriessen and Elise Welberg and Bruna G Dutra and Praneeta R Konduri and Nerea Arrarte Terreros and Jan W Hoving and Manon L Tolhuisen and Manon Kappelhof and Josje Brouwer and Nikki Boodt and Katinka R van Kranendonk and Miou S Koopman and Hajo M Hund and Menno Krietemeijer and Wim H van Zwam and Heleen M M van Beusekom and Aad van der Lugt and Bart J Emmer and Henk A Marquering and Yvo B W E M Roos and Matthan W A Caan and Charles B L M Majoie},
  title = {Thrombus radiomics in patients with anterior circulation acute ischemic stroke undergoing endovascular treatment},
  journal = {Journal of {NeuroInterventional} Surgery}
}
""",

    "Freund1997": r"""
@article{Freund1997,
  author  = {Yoav Freund and Robert E. Schapire},
  title   = {A Decision-Theoretic Generalization of On-Line Learning and an Application to Boosting},
  journal = {Journal of Computer and System Sciences},
  volume  = {55},
  number  = {1},
  pages   = {119--139},
  year    = {1997},
  doi     = {10.1006/jcss.1997.1504},
}
""",

    "Nadeau2003": r"""
@article{Nadeau2003,
  author  = {Claude Nadeau and Yoshua Bengio},
  title   = {Inference for the Generalization Error},
  journal = {Machine Learning},
  volume  = {52},
  number  = {3},
  pages   = {239--281},
  year    = {2003},
  doi     = {10.1023/A:1024068626366},
}
""",

}
