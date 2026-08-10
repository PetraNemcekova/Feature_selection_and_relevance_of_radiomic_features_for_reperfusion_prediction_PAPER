These instructions come from <https://github.com/tomasvicar/overleaf_agents>.
Keep that link here: it is where the compile image, the TeX Live package list,
and any fix to either of them live.

## Building the paper

Compile in the pinned container — do not install TeX Live and do not try to run
`pdflatex` directly on the host:

```bash
docker run --rm -v "$PWD:/work" -u "$(id -u):$(id -g)" \
  ghcr.io/tomasvicar/latex-overleaf:TL2025
```

- Produces `main.pdf` in the repo root; aux files go to `build/` (gitignored).
  With no argument the entrypoint takes `main.tex`, or the single top-level
  `.tex` that has a `\documentclass` if the manuscript is named otherwise; if
  several qualify it stops and asks for a name. The PDF is named after the
  source, so check `.gitignore` ignores that name.
- The `TL2025` tag pins the image to the same TeX Live release as the Overleaf
  project, so a successful local compile means it compiles on Overleaf too. Use
  that tag, not `:latest` — `:latest` moves to a new TeX Live year when the
  upstream repo does. Confirmed against Menu → Settings → TeX Live version in
  the Overleaf project itself.
- On failure the container prints the relevant error lines; the full log is
  `build/main.log`. Read the **first** error — later ones are usually fallout.
- Never commit `main.pdf` fixes by hand. Fix the `.tex` and rebuild.

If the build fails on a missing `.sty`, the image lacks that package. Do not
work around it by rewriting the manuscript — report it, so it can be added to
`packages.txt` in the `overleaf_agents` repo. For an immediate local unblock,
extend the image:

```bash
docker build -t latex-overleaf:local - <<'EOF'
FROM ghcr.io/tomasvicar/latex-overleaf:TL2025
RUN tlmgr install PACKAGE && kpsewhich PACKAGE.sty
EOF
```

and compile with `latex-overleaf:local`. Keep the `kpsewhich`: `tlmgr install`
exits 0 even when the download failed, so it is the only thing that turns a
silent failure into a failed build.

## Syncing with Overleaf

The `overleaf` remote (`https://git.overleaf.com/6a54a532bc5a575cee84418c`,
branch `main`) is always present. A GitHub remote named `origin` is optional —
check with `git remote` and push to it only if it exists.

```bash
git pull overleaf main --no-rebase   # before starting work, and after a rejected push
git add -A && git commit -m "..."
git push overleaf main
git remote | grep -q '^origin$' && git push origin main
```

Rules that matter:

- **Never force-push.** Overleaf rejects it outright, and it would destroy edits
  made in the browser.
- If `git push overleaf main` is rejected, someone edited the project in the
  Overleaf UI. Pull with `--no-rebase`, resolve conflicts in the `.tex` source,
  then push again. Do not rebase over Overleaf's commits.
- Always compile successfully before pushing to Overleaf. A broken build there
  is visible to every co-author immediately.
- If an `origin` remote exists, push there too, or the two drift apart. Do not
  add one on your own initiative — Overleaf-only is a valid setup.

## Comments and review

Overleaf's comment threads and track changes live in Overleaf's database, not
in the files. They do not arrive with a clone, and a commit cannot answer one.
Leave anything that needs saying in the source instead:

- `\todo{...}` (`todonotes`) renders in the PDF margin, which is the only place
  a co-author working in the browser will see it. A plain `%` comment reaches
  whoever edits the source next, and nobody else.
- Mark substantive rewrites with `changes`: `\added{}`, `\deleted{}`,
  `\replaced{}`.

Both hide their markup for submission without deleting it, but the options
differ: `\usepackage[final]{changes}` and `\usepackage[final,obeyFinal]{todonotes}`.
`[final]` on its own does nothing in `todonotes`.

To show what changed between two revisions, build the marked-up PDF rather than
describing it in prose:

```bash
git show <rev>:main.tex > old.tex
docker run --rm -v "$PWD:/work" -u "$(id -u):$(id -g)" \
  ghcr.io/tomasvicar/latex-overleaf:TL2025 latexdiff old.tex main.tex > diff.tex
docker run --rm -v "$PWD:/work" -u "$(id -u):$(id -g)" \
  ghcr.io/tomasvicar/latex-overleaf:TL2025 diff.tex
```

Delete `old.tex`, `diff.tex` and `diff.pdf` afterwards — they are not part of
the manuscript and must not be committed. For a journal word limit, run
`texcount -1 -sum main.tex` through the container the same way.

More on all of this — comment conventions, review rounds, git habits:
<https://github.com/tomasvicar/overleaf_agents/blob/main/docs/tips.md>.

## Conventions

- Never edit `*.cls` or `*.bst` files — they are the journal's, and the journal
  will use its own copies anyway.
- One sentence per line. LaTeX ignores single newlines, so the PDF is unchanged,
  but a diff then shows the sentence that changed rather than a repainted
  paragraph, and a merge with an Overleaf edit resolves per sentence. Keep the
  existing line structure of a paragraph you are editing; do not reflow one you
  are not.
- Bibliography entries go in the `.bib` file, never inline in the `.tex`.
- Figures are referenced by `\label`/`\ref`, never by hardcoded numbers.
- Everything committed here syncs into the Overleaf project and appears in every
  co-author's browser. Scratch files, analysis scripts and notes belong outside
  this repository.
- Numbers in the text come from the analysis outputs, never from memory. If you
  cannot find the source for one, say so rather than carrying it forward.

## This repository specifically

- The manuscript is `main.tex` (renamed from Overleaf's default
  `elsarticle-template-num-CMPB.tex`); target journal: Computerized Medical
  Imaging and Graphics (`\journal{}` in the preamble).
- `elsarticle-template-harv.tex`, `elsarticle-template-num.tex`,
  `elsarticle-template-num-names.tex`, `elsarticle.dtx`, `elsarticle.ins`,
  `manifest.txt`, `changelog.txt` and the top-level `README` are unused
  boilerplate left over from Overleaf's elsarticle template gallery entry —
  not part of the manuscript, safe to ignore or remove. `elsarticle.cls`
  itself comes from the TeX Live image, not from `elsarticle.dtx` in this repo.
- `doc/` holds the figures `main.tex` includes (`\includegraphics{doc/...}`) —
  keep paths relative to the repo root.
- `Supplement/supplement_B.tex` and `VanVoorst2022/` (reference PDFs) are
  supporting material, not compiled as part of `main.tex`.
