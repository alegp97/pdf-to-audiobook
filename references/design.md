# Design and provenance

This skill bundles an adapted subset of the MIT-licensed SimpleAudioBookGen 1.0.0 core plus its optional Qt desktop menu. The original app uses PyMuPDF, text-cleaning rules, Spanish normalization, segmentation, Edge-TTS/Windows voices, pydub, and FFmpeg. No dependency on its original checkout remains; Qt is needed only for the menu.

Changes in this edition:

- Relative resource discovery and platform-neutral paths, with no personal installation paths.
- English user-facing interface, transcript/report exports, and English default voice.
- Voice catalog filtering by language/locale, with language inferred from a selected Edge voice when unspecified.
- Spanish linguistic normalization only for Spanish narration; conservative preservation for other languages. Voices do not translate text.
- English/Spanish chapter recognition, preserved prefaces, narrated chapter titles, and retained short text chunks.
- Header candidates counted once per page; chapter headings protected; only complete recurring lines removed.
- Separate per-conversion temporary directories and decoded-audio validation before delivery.
- SAPI objects created/used on the same thread; direct COM file output avoids the pyttsx3 blocking behavior seen during local testing.
- Bundled FFmpeg fallback through imageio-ffmpeg, without requiring a separate FFprobe executable.
- A self-contained GUI launcher with per-user settings/logs, detached startup, English defaults, optional PDF preselection, and an offline offscreen smoke check. The original GUI layout and controls are preserved. SAPI worker threads initialize Windows COM; preview filenames safely handle installed voice IDs. The GUI warns before overwriting an existing MP3.

The CLI's transcript preview, mixed-page checks, batch reports, and full MP3 validation remain CLI features. The GUI retains the original document estimates, preview, and conversion flow; its static voice menu is not a live catalog. It also exposes the original optional Kokoro/Piper modes; their packages/models are manual installs and not included. The settings location is separate from the original app.

Online synthesis uses four workers; SAPI synthesis is serial and Windows-only. Output defaults match the app: 192 kbps, target loudness -20 dBFS, 200 ms sentence pauses, and 1,800 ms chapter pauses.

The inherited extractor rejects documents below 50 characters per page on average. The adapter additionally rejects image-bearing pages with little selectable text. Those checks are conservative, not a comprehensive OCR classifier. A successful extraction is not proof of correct column/table reading order; review the transcript.

The inherited assembler holds decoded audio in memory. Very long audiobooks may exceed available RAM. Online synthesis failures stop a document's conversion, while other documents in the batch can continue. No automatic voice substitution is made.
