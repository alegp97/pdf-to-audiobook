# PDF to Audiobook 1.2 — ElevenLabs, with natural long-form cadence

Give your PDFs a voice.

Version 1.2 adds ElevenLabs as a first-class narration engine in both the CLI and the bundled desktop menu. Configure `ELEVENLABS_API_KEY` in the process environment or the private, Git-ignored `.env` file, then list the voices visible to that account. The GUI loads those voices live, shows their names and categories, and retains manual voice-ID entry if the catalog is unavailable. The key is never written to settings, reports, or logs.

Long-form ElevenLabs narration now favors continuous prosody instead of audible fragment boundaries. Layout-only paragraph breaks are coalesced, requests use 9,000-character chunks by default, neighboring text and request-stitching IDs preserve context, and assembly follows the actual punctuation: no added pause without punctuation, a short pause after commas, and a natural sentence pause after terminal punctuation. Meeting timestamps and invisible PDF markers are removed before narration, and unexplained generated silence is compressed.

The selected output folder now receives only the finished MP3. Dry-run review files live under `work/pdf-to-audiobook/review`; ordinary successful conversions remove review files and logs, failures retain diagnostics under `failed`, and `--keep-artifacts` preserves them explicitly under `artifacts`. The CLI still validates the decoded MP3 before delivery, preserves successful files in a partially failed batch, and never silently substitutes a voice or speech provider.

The existing Edge-TTS and Windows SAPI workflows remain available. The desktop menu remains portable and keeps PDF selection, output choice, voice preview, estimates, progress, and per-user settings. Qt is optional for CLI-only use. Generated-fixture tests cover the new engine, segmentation, silence policy, artifact lifecycle, live voice-menu behavior, and error handling without making paid speech requests during the offline suite.

Local validation was performed on Windows; the GitHub Actions matrix must still be checked after publication on Windows, Linux, and macOS. OCR is not included, complex layouts still require transcript review, and ElevenLabs synthesis can consume account credits.

Adapted from the MIT-licensed SimpleAudioBookGen core, with its attribution preserved. Third-party dependency licenses and online service terms continue to apply.
