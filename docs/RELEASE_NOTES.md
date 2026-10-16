# PDF to Audiobook 1.1 — The desktop menu is back

Give your PDFs a voice.

Open the bundled desktop menu from Python or ask the agent skill to open it. The SimpleAudioBookGen-derived window includes PDF selection, voice/language settings, audio quality, preview, estimates, and progress. The GUI is portable and uses per-user settings; it does not need the original project folder. Install `scripts/requirements-gui.txt` and run `scripts/launch_gui.py`.

Direct CLI conversion remains available, with local text preview, batch reports, and decoded-audio validation before delivery. Qt is optional. Both the menu and CLI preserve the document's language.

The converter preserves document beginnings, chapter titles, and short passages. English/Spanish chapter recognition is included; Spanish linguistic normalization applies only to Spanish text. Online voices use Edge-TTS, while Windows users can choose installed SAPI voices for offline narration.

The source includes generated-fixture tests, a menu/preferences smoke check, and a GitHub Actions matrix for Windows, Linux, macOS. Local validation was performed on Windows; cross-platform CI results must be checked after publication. OCR is not included, and complex PDF layouts require transcript review.

Adapted from the MIT-licensed SimpleAudioBookGen core, with its attribution preserved. Third-party dependency licenses and online service terms continue to apply.
