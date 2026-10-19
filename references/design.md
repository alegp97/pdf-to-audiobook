# Design and provenance

This skill bundles an adapted subset of the MIT-licensed SimpleAudioBookGen 1.0.0 core plus its optional Qt desktop menu. The original app uses PyMuPDF, text-cleaning rules, Spanish normalization, segmentation, Edge-TTS/Windows voices, pydub, and FFmpeg. No dependency on its original checkout remains; Qt is needed only for the menu.

Changes in this edition:

- Relative resource discovery and platform-neutral paths, with no personal installation paths.
- English user-facing interface, transcript/report exports, and English default voice.
- Voice catalog filtering by language/locale, with language inferred from a selected Edge voice when unspecified, plus ElevenLabs account voice IDs supplied explicitly by the user.
- Spanish linguistic normalization only for Spanish narration; conservative preservation for other languages. Voices do not translate text.
- English/Spanish chapter recognition, preserved prefaces, narrated chapter titles, and retained short text chunks.
- Header candidates counted once per page; chapter headings protected; only complete recurring lines removed.
- Separate per-conversion temporary directories and decoded-audio validation before delivery.
- SAPI objects created/used on the same thread; direct COM file output avoids the pyttsx3 blocking behavior seen during local testing.
- Bundled FFmpeg fallback through imageio-ffmpeg, without requiring a separate FFprobe executable.
- A self-contained GUI launcher with per-user settings/logs, detached startup, English defaults, optional PDF preselection, and an offline offscreen smoke check. The original GUI layout and controls are preserved. The ElevenLabs selector loads the authenticated account's live voice catalog and falls back to editable voice-ID entry on API errors. SAPI worker threads initialize Windows COM; preview filenames safely handle installed voice IDs. The GUI warns before overwriting an existing MP3.
- User-selectable output directories in both workflows. The agent asks for a destination and offers the Desktop; the GUI and standalone CLI use the Desktop as their default while still accepting another path.
- Clean output destinations: only final MP3 files are placed there. Dry-run material lives under the work directory's `review` folder and is removed with the log after a successful final conversion. Failure evidence is retained under `failed`; `--keep-artifacts` explicitly preserves successful-run material under `artifacts`.

The CLI's transcript preview, mixed-page checks, batch reports, and full MP3 validation remain CLI features. Transcripts, reports, logs, and temporary chunks never need to share the chosen audiobook destination. The GUI retains the original document estimates, preview, and conversion flow. Its Edge catalog remains bundled, while its ElevenLabs selector loads the authenticated account's live voice catalog and keeps editable voice-ID entry as a fallback. It also exposes the original optional Kokoro/Piper modes; their packages/models are manual installs and not included. The settings location is separate from the original app.

Edge synthesis uses four workers. ElevenLabs synthesis is serial to avoid unexpected concurrent credit usage and account rate-limit pressure; SAPI synthesis is also serial and Windows-only. Output defaults match the app: 192 kbps, target loudness -20 dBFS, 200 ms sentence pauses, and 1,800 ms chapter pauses.

ElevenLabs credentials are read from `ELEVENLABS_API_KEY`. An existing process value takes priority; otherwise the integration loads the private, Git-ignored `.env` file at the skill root. The key is never serialized into YAML settings or reports. The integration uses the official Python SDK, `eleven_multilingual_v2`, and `mp3_44100_128` by default; both API parameters remain configurable from the CLI.

ElevenLabs uses 9,000-character chunks by default, below the 10,000-character limit of `eleven_multilingual_v2`. Layout-only paragraph breaks are coalesced so they do not become request boundaries. When multiple requests are unavoidable, the integration supplies up to 500 characters of future context and up to three prior request IDs using ElevenLabs Request Stitching; models in the `eleven_v3` family fall back to text context because they do not support that feature. Timestamped character alignment classifies generated silences: unexplained gaps are removed, comma/semicolon/colon pauses are shortened to 120 ms, and sentence-ending punctuation retains 320 ms. During assembly, leading silence is removed and trailing silence is retained only when justified by punctuation; no separate inter-chunk pause is inserted. Meeting-transcript timestamps and zero-width layout markers are removed before narration.

The inherited extractor rejects documents below 50 characters per page on average. The adapter additionally rejects image-bearing pages with little selectable text. Those checks are conservative, not a comprehensive OCR classifier. A successful extraction is not proof of correct column/table reading order; review the transcript.

The inherited assembler holds decoded audio in memory. Very long audiobooks may exceed available RAM. Online synthesis failures stop a document's conversion, while other documents in the batch can continue. No automatic voice substitution is made.
