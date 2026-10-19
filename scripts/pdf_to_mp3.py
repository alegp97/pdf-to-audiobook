"""Headless batch adapter for the MIT SimpleAudioBookGen core."""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))


def configure_ffmpeg() -> str:
    import imageio_ffmpeg
    ffmpeg = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
    # pydub needs ffprobe for compressed input. Only use an installed pair;
    # otherwise convert each input to WAV using the bundled ffmpeg before decoding.
    from pydub import AudioSegment
    from audiobook_gen.utils.ffmpeg_process import install_hidden_ffmpeg_processes
    AudioSegment.converter = ffmpeg
    install_hidden_ffmpeg_processes()
    if not getattr(AudioSegment.from_file, "_portable_audiobook", False):
        original_from_file = AudioSegment.from_file

        def from_file_without_probe(file, format=None, *args, **kwargs):
            if isinstance(file, (str, Path)) and Path(file).suffix.lower() == ".wav":
                with open(file, "rb") as audio_input:
                    return original_from_file(audio_input, format="wav", *args, **kwargs)
            if isinstance(file, (str, Path)) and not shutil.which("ffprobe"):
                proc = subprocess.run(
                    [ffmpeg, "-v", "error", "-i", str(file), "-f", "wav", "pipe:1"],
                    capture_output=True, check=True, timeout=180,
                    **hidden_process_options(),
                )
                import io
                return original_from_file(io.BytesIO(proc.stdout), format="wav")
            return original_from_file(file, format=format, *args, **kwargs)

        from_file_without_probe._portable_audiobook = True
        AudioSegment.from_file = staticmethod(from_file_without_probe)
    return ffmpeg


def hidden_process_options() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def prepare(pdf: Path, settings, text_path: Path) -> dict:
    import pymupdf as fitz
    from audiobook_gen.core.pdf_extractor import PDFExtractor
    from audiobook_gen.core.text_cleaner import TextCleaner
    from audiobook_gen.core.text_normalizer import TextNormalizer
    from audiobook_gen.core.text_segmenter import TextSegmenter

    extracted = PDFExtractor().extract(pdf)
    with fitz.open(pdf) as doc:
        suspect = [
            page.number + 1 for page in doc
            if len(page.get_text().strip()) < 50 and page.get_images()
        ]
    if suspect:
        raise ValueError(
            f"Pages with images and little selectable text: {suspect}. "
            "Review/OCR is needed before narrating the complete document."
        )
    cleaned = TextCleaner(settings.cleaner).clean(extracted.pages)
    normalized = (TextNormalizer(settings.normalization_rules_path).normalize(cleaned.full_text)
                  if settings.tts.language == "Spanish" else cleaned.full_text.strip())
    chunks = TextSegmenter(settings.segmenter).segment(normalized)
    if not chunks:
        raise ValueError("No narratable text remains after cleanup.")
    # Save exactly what the engine will say, not internal chapter markers.
    spoken = "\n\n".join(chunk.text for chunk in chunks)
    text_path.write_text(spoken, encoding="utf-8")
    return {
        "pages": extracted.metadata.total_pages,
        "characters": len(spoken), "chunks": len(chunks),
        "chapters": len(cleaned.chapters), "narrated_text": str(text_path),
    }


def validate_mp3(ffmpeg: str, path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("No valid MP3 was generated.")
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-xerror", "-i", str(path), "-map", "0:a:0", "-progress", "pipe:1", "-nostats", "-f", "null", "-"],
        capture_output=True, text=True, timeout=600, **hidden_process_options(),
    )
    if proc.returncode:
        raise RuntimeError("MP3 decoding failed: " + proc.stderr[-1500:])
    times = [int(line.split("=", 1)[1]) for line in proc.stdout.splitlines() if line.startswith("out_time_us=") and line.split("=", 1)[1].isdigit()]
    duration = max(times, default=0) / 1_000_000
    if duration <= 0:
        raise RuntimeError("The MP3 does not contain audio of positive duration.")
    return {"audio_validated": True, "bytes": path.stat().st_size, "audio_duration_seconds": round(duration, 2)}


def unique_stem(directory: Path, stem: str) -> str:
    candidate = stem
    index = 2
    while (directory / f"{candidate}.mp3").exists():
        candidate = f"{stem}_{index}"
        index += 1
    return candidate


def report_path(directory: Path) -> Path:
    index = 1
    path = directory / "report.json"
    while path.exists():
        index += 1
        path = directory / f"report_{index}.json"
    return path


def remove_owned_directory(path: Path, work: Path) -> None:
    """Remove one known child directory without ever widening the cleanup scope."""
    resolved_path = path.resolve()
    resolved_work = work.resolve()
    if resolved_path.parent != resolved_work:
        raise ValueError(f"Refusing to clean a directory outside the work folder: {path}")
    if resolved_path.is_dir():
        shutil.rmtree(resolved_path)


def parse_args():
    from audiobook_gen.paths import default_output_dir

    parser = argparse.ArgumentParser(description="Turn readable PDFs into MP3 audiobooks.")
    parser.add_argument("pdfs", nargs="*", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir(),
        help="Destination folder (default: your Desktop).",
    )
    parser.add_argument("--work-dir", type=Path, default=Path.cwd() / "work" / "pdf-to-audiobook")
    parser.add_argument("--language", help="Language/locale code, e.g. en, es, fr, or en-GB. Defaults to the voice's language.")
    parser.add_argument("--voice", default=None, help="Voice name for Edge/SAPI or voice ID for ElevenLabs.")
    parser.add_argument("--engine", choices=("edge", "elevenlabs", "sapi"), default="edge")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--elevenlabs-model", default="eleven_multilingual_v2")
    parser.add_argument("--elevenlabs-output-format", default="mp3_44100_128")
    parser.add_argument("--elevenlabs-chunk-chars", type=int, default=9000)
    parser.add_argument("--elevenlabs-context-chars", type=int, default=500)
    parser.add_argument("--bitrate", choices=("64k", "96k", "128k", "192k", "256k", "320k"), default="192k")
    parser.add_argument("--keep-headers", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep transcript, report, and log in the work folder after a successful conversion.",
    )
    parser.add_argument("--list-voices", action="store_true")
    args = parser.parse_args()
    if not args.pdfs and not args.list_voices:
        parser.error("Provide one or more PDF paths.")
    if args.engine == "sapi" and os.name != "nt":
        parser.error("SAPI offline narration is available only on Windows.")
    return args


DEFAULT_VOICES = {"en": "en-US-GuyNeural", "es": "es-ES-AlvaroNeural"}


def resolve_voice(language: str | None, voice: str | None, engine: str) -> tuple[str, str]:
    if engine == "sapi":
        return voice or "System Default", (language or "en").lower()
    if engine == "elevenlabs":
        if not voice:
            raise ValueError(
                "Select an ElevenLabs voice ID with --voice. "
                "Discover account voices using --list-voices --engine elevenlabs."
            )
        return voice, (language or "en").lower().replace("_", "-")
    inferred = voice.split("-", 1)[0].lower() if voice else "en"
    code = (language or inferred).lower().replace("_", "-")
    if voice:
        if code.split("-", 1)[0] != inferred:
            raise ValueError("The language and voice do not match. Use a voice for the document's language.")
        return voice, code
    if code in DEFAULT_VOICES:
        return DEFAULT_VOICES[code], code
    raise ValueError("Select a voice for this language/locale with --voice. Discover voices using --list-voices --language " + code)


def main() -> int:
    args = parse_args()
    if args.list_voices:
        if args.engine == "sapi":
            import win32com.client
            engine = win32com.client.Dispatch("SAPI.SpVoice")
            print(json.dumps([{"id": v.Id, "name": v.GetDescription()} for v in engine.GetVoices()], ensure_ascii=False, indent=2))
        elif args.engine == "elevenlabs":
            from audiobook_gen.core.tts_engine import list_elevenlabs_voices
            print(json.dumps(list_elevenlabs_voices(), ensure_ascii=False, indent=2))
        else:
            import asyncio
            import edge_tts
            voices = asyncio.run(edge_tts.list_voices())
            if args.language:
                code = args.language.lower().replace("_", "-")
                voices = [v for v in voices if v["Locale"].lower() == code or v["Locale"].lower().startswith(code + "-")]
            print(json.dumps(voices, ensure_ascii=False, indent=2))
        return 0

    voice, language = resolve_voice(args.language, args.voice, args.engine)

    output = args.output_dir.resolve()
    work = args.work_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    from audiobook_gen.config import Settings
    from audiobook_gen.utils.logger import setup_logger
    from audiobook_gen.pipeline import AudioBookPipeline
    log_path = work / "conversion.log"
    setup_logger(str(log_path))
    ffmpeg = configure_ffmpeg() if not args.dry_run else None
    results = []
    artifact_directory = work / ("artifacts" if args.keep_artifacts else "review") if (args.keep_artifacts or args.dry_run) else None
    if artifact_directory:
        artifact_directory.mkdir(parents=True, exist_ok=True)
    if args.engine == "edge" and not args.dry_run:
        print("Online Edge-TTS voice: text fragments are sent to the speech service.", flush=True)
    elif args.engine == "elevenlabs" and not args.dry_run:
        print(
            "Online ElevenLabs voice: text fragments are sent to ElevenLabs and may use paid API credits.",
            flush=True,
        )

    for pdf in args.pdfs:
        pdf = pdf.resolve()
        stem = unique_stem(output, pdf.stem)
        final_path = output / f"{stem}.mp3"
        entry = {"input": str(pdf), "success": False, "dry_run": args.dry_run}
        temp_context = None
        transcript_path = None
        print(f"Processing: {pdf.name}", flush=True)
        try:
            temp_context = tempfile.TemporaryDirectory(prefix="conversion-", dir=work)
            temp = Path(temp_context.name)
            settings = Settings(temp_dir=str(temp))
            settings.tts.engine = args.engine
            settings.tts.voice = voice
            settings.tts.language = "Spanish" if language.split("-", 1)[0] == "es" else "Other"
            settings.tts.rate = args.rate
            settings.tts.pitch = args.pitch
            settings.tts.elevenlabs_model = args.elevenlabs_model
            settings.tts.elevenlabs_output_format = args.elevenlabs_output_format
            settings.tts.elevenlabs_chunk_chars = args.elevenlabs_chunk_chars
            settings.tts.elevenlabs_context_chars = args.elevenlabs_context_chars
            settings.audio.mp3_bitrate = args.bitrate
            settings.segmenter.min_chunk_chars = 1
            if args.engine == "elevenlabs":
                settings.segmenter.max_chunk_chars = args.elevenlabs_chunk_chars
            settings.cleaner.min_line_length = 1
            if args.keep_headers:
                settings.cleaner.header_footer_threshold = 2.0
            if args.engine != "edge" and (args.rate != "+0%" or args.pitch != "+0Hz"):
                raise ValueError(
                    f"{args.engine} rate/pitch adjustments are not implemented in this adapter."
                )
            transcript_path = (artifact_directory / f"{stem}.txt") if artifact_directory else (temp / f"{stem}.txt")
            entry.update(prepare(pdf, settings, transcript_path))
            entry.update(
                voice=settings.tts.voice,
                language=language,
                engine=args.engine,
                bitrate=args.bitrate,
            )
            if args.engine == "elevenlabs":
                entry.update(
                    model=args.elevenlabs_model,
                    output_format=args.elevenlabs_output_format,
                )
            if args.dry_run:
                entry["success"] = True
                print(f"Transcript ready: {entry['pages']} pages, {entry['characters']} characters, {entry['chunks']} chunks.", flush=True)
            else:
                def progress(p):
                    print(f"{p.progress:.0%} | {p.state.value} | {p.detail or p.message}", flush=True)

                partial = temp / "result.mp3"
                result = AudioBookPipeline(settings, progress).run(str(pdf), str(partial))
                if not result.success:
                    raise RuntimeError(result.error or "Conversion failed")
                entry.update(validate_mp3(ffmpeg, partial))
                # Exclusive creation: even a concurrent writer cannot be overwritten.
                with final_path.open("xb") as destination, partial.open("rb") as source:
                    shutil.copyfileobj(source, destination)
                entry.update(success=True, output=str(final_path), conversion_seconds=result.duration_secs)
                print(f"MP3 ready: {final_path}", flush=True)
        except Exception as exc:
            if transcript_path and transcript_path.is_file() and artifact_directory is None:
                failure_directory = work / "failed"
                failure_directory.mkdir(parents=True, exist_ok=True)
                retained_transcript = failure_directory / f"{stem}.txt"
                shutil.copy2(transcript_path, retained_transcript)
                entry["narrated_text"] = str(retained_transcript)
            entry["error"] = str(exc)
            print(f"ERROR: {pdf.name}: {exc}", file=sys.stderr, flush=True)
        finally:
            if temp_context is not None:
                temp_context.cleanup()
        results.append(entry)

    success = all(r["success"] for r in results)
    report = None
    if artifact_directory is not None or not success:
        report_directory = artifact_directory or (work / "failed")
        report_directory.mkdir(parents=True, exist_ok=True)
        for entry in results:
            narrated_text = entry.get("narrated_text")
            if narrated_text and not Path(narrated_text).is_file():
                entry.pop("narrated_text")
        report = report_path(report_directory)
        report.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Artifacts: {report_directory}", flush=True)

    logging.shutdown()
    if success and not args.dry_run and not args.keep_artifacts:
        remove_owned_directory(work / "review", work)
        log_path.unlink(missing_ok=True)
        print("Auxiliary review files cleaned up.", flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Conversion interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
