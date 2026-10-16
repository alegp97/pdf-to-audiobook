# Contributing

Contributions should improve faithful narration, portability, and clear failure behavior. Useful areas include language-aware normalization, PDF reading order, resumable synthesis, and lower-memory assembly.

Create a virtual environment, install `scripts/requirements.txt`, and run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

For menu changes, also install `scripts/requirements-gui.txt` and run `python scripts/launch_gui.py --smoke-test`. This opens and closes an offscreen window with temporary settings, checks the voice menu/preferences, and makes no online speech requests. Without optional Qt dependencies, GUI window tests are skipped and CLI checks remain available.

Use generated fixtures, not personal documents, for tests. Offline tests must not contact a speech service. Include the input shape, observed behavior, expected behavior, and relevant Python/OS versions when reporting a bug. For a pull request, explain the behavioral change and how it was verified.

Preserve third-party license notices. Do not commit PDFs, audio exports, credentials, machine-specific paths, or virtual environments. New language rules should apply only to that language and should preserve short passages and document beginnings/endings.
