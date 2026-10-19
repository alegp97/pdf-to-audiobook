# Third-party notices

The adapted `scripts/vendor/audiobook_gen` core, voice catalog, and optional Qt desktop interface originate in SimpleAudioBookGen, copyright (c) 2026 SimpleAudioBookGen contributors. Its original MIT license is included at `scripts/vendor/LICENSE` and remains applicable to that code. Adaptations and their purpose are recorded in `references/design.md`.

The repository does not include third-party Python distributions, FFmpeg executables, voice models, or user documents. Installation obtains dependencies separately. Their license notices and any usage terms remain applicable; this repository's MIT license does not relicense them.

In particular, review PyMuPDF's licensing for your distribution/use case, and the licensing of the FFmpeg build selected at runtime. Online speech processing also depends on each provider's terms, including ElevenLabs account, usage, and voice rights, separately from the licenses of the `edge-tts` and `elevenlabs` clients. Inspect the installed distributions and upstream projects before redistributing an application bundle or offering a commercial service.
