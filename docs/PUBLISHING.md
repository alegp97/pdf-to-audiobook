# Publish on GitHub

This is a source-ready repository, not a claim that a GitHub repository already exists. Choose the account or organization that should own it before publishing.

Suggested repository name: `pdf-to-audiobook`

Suggested description:

> Give your PDFs a voice. A portable agent skill and Python CLI for turning readable PDFs into verified MP3 audiobooks.

Suggested topics: `pdf`, `audiobook`, `text-to-speech`, `edge-tts`, `python`, `agent-skills`, `codex`, `accessibility`.

## Create the repository

From this folder, with Git and GitHub CLI installed and authenticated:

```bash
git init -b main
git add .
git commit -m "Release portable PDF to Audiobook skill"
gh repo create pdf-to-audiobook --public --source . --remote origin --push
```

If publishing from an organization, use its repository name instead of the personal-account name in `gh repo create`. If the destination already exists, add its remote and push using the existing repository workflow rather than trying to create it again. Keep your normal Git author identity.

Alternatively, create an empty public repository on GitHub and follow its instructions to push an existing folder. The repository includes a workflow under `.github/workflows/tests.yml`; check all nine CLI/GUI jobs after the first push.

## First release

After CI passes, tag a release and attach the source ZIP:

```bash
git tag v1.1.0
git push origin v1.1.0
gh release create v1.1.0 --title "PDF to Audiobook 1.1 — Desktop Menu" --notes-file docs/RELEASE_NOTES.md
```

Use a repository source archive or the prepared ZIP; do not upload virtual environments, PDF documents, generated personal audio, or local work folders.

Set the repository description/topics. The README banner is already included and renders without external image hosting; use `docs/banner.svg` as a source if you later create a raster social preview.
