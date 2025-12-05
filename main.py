import os
import json
from dotenv import load_dotenv

from inputs.url_extractor import get_active_url
from inputs.transcript_collector import collect_youtube_transcript
from inputs.youtube_audio_extractor import download_audio
from inputs.speech_to_text import ensure_wav16k, speech_to_text_from_file, build_record_from_file
from inputs.schema import append_jsonl
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

load_dotenv()

OUT_JSONL = "out/youtube.jsonl"
AUDIO_DIR = "out/audio"
LAST_RUN = "out/last_run.json"


def write_last_run(data: dict, path: str = LAST_RUN):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def main():
    # 1) Lấy URL từ trình duyệt
    print("[1/4] Đang lấy URL từ trình duyệt...")
    result = get_active_url()

    if "error" in result:
        print(f"❌ Lỗi khi lấy URL: {result['error']}")
        return

    url = result.get("url", "")
    title = result.get("title", "")

    if not url:
        print("❌ Không lấy được URL từ trình duyệt")
        return

    print(f"✓ URL: {url}")
    print(f"✓ Title: {title}\n")

    # 2) Lấy transcript Youtube
    print("[2/4] Đang thử lấy transcript từ YouTube...")
    try:
        rec = collect_youtube_transcript(
            url,
            languages=("vi", "en"),
            out_path=OUT_JSONL,
        )

        print(f"✓ Transcript OK! ID: {rec.id}")

        if rec.text:
            preview = rec.text[:100] + "..." if len(rec.text) > 100 else rec.text
            print(f"✓ Text: {preview}")

        write_last_run({
            "timestamp": rec.meta.get("created_at"),
            "url": url,
            "title": title,
            "source": "youtube_transcript",
            "record_id": rec.id,
            "transcript": rec.text
        })

        return

    except (NoTranscriptFound, TranscriptsDisabled) as e:
        print(f"⚠ Không lấy được transcript: {e}")
        print("→ Chuyển sang tải audio + chuyển giọng nói thành text...\n")
    except Exception as e:
        print(f"⚠ Lỗi không xác định: {e}")
        print("→ Chuyển sang tải audio + chuyển giọng nói thành text...\n")

    # 3) Tải audio từ YouTube
    print("[3/4] Đang tải audio từ YouTube...")

    try:
        existing_files = set()
        if os.path.exists(AUDIO_DIR):
            existing_files = {
                f for f in os.listdir(AUDIO_DIR)
                if os.path.isfile(os.path.join(AUDIO_DIR, f))
            }

        download_audio(url, outdir=AUDIO_DIR, allow_playlist=False)

        # Lọc file mới
        new_files = []
        for f in os.listdir(AUDIO_DIR):
            fp = os.path.join(AUDIO_DIR, f)
            if os.path.isfile(fp) and f not in existing_files:
                new_files.append((fp, os.path.getmtime(fp)))

        # Nếu không thấy file mới → lấy file gần nhất
        if not new_files:
            all_files = [
                (os.path.join(AUDIO_DIR, f), os.path.getmtime(os.path.join(AUDIO_DIR, f)))
                for f in os.listdir(AUDIO_DIR)
                if os.path.isfile(os.path.join(AUDIO_DIR, f))
            ]
            if all_files:
                new_files = [max(all_files, key=lambda x: x[1])]

        if not new_files:
            raise RuntimeError("Không tìm thấy file audio đã tải về")

        audio_file = max(new_files, key=lambda x: x[1])[0]
        print(f"✓ Đã tải audio: {os.path.basename(audio_file)}\n")

    except Exception as e:
        print(f"❌ Lỗi khi tải audio: {e}")
        return

    # 4) Speech-to-text Google STT
    print("[4/4] Đang chuyển audio → text bằng Google Speech-to-Text...")

    try:
        # Chuẩn hóa audio
        wav_file = ensure_wav16k(audio_file)
        print(f"✓ Chuẩn hóa audio: {os.path.basename(wav_file)}")

        # STT
        stt_text = speech_to_text_from_file(wav_file)
        print(f"✓ STT thành công")
        preview = stt_text[:100] + "..." if len(stt_text) > 100 else stt_text
        print(f"✓ Text: {preview}")

        # Tạo record Pydantic
        video_id = os.path.splitext(os.path.basename(audio_file))[0]

        rec = build_record_from_file(
            video_id=video_id,
            audio_local_path=wav_file,
            text=stt_text
        )

        append_jsonl(OUT_JSONL, rec)

        write_last_run({
            "timestamp": rec.meta.get("created_at"),
            "url": url,
            "title": title,
            "source": "google_stt",
            "record_id": rec.id,
            "audio_file": os.path.basename(audio_file),
            "transcript": stt_text,
        })

        print(f"✓ Lưu file JSONL → {OUT_JSONL}")
        print(f"✓ Record ID: {rec.id}")

    except Exception as e:
        print(f"❌ Lỗi khi chạy STT: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n✅ Hoàn thành!")


if __name__ == "__main__":
    main()
