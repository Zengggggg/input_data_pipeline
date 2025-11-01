import os
from inputs.url_extractor import get_active_url
from inputs.transcript_collector import collect_youtube_transcript
from inputs.youtube_audio_extractor import download_audio
from inputs.speech_to_text import ensure_wav16k, stt_vosk, build_record_from_file
from inputs.schema import append_jsonl
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

OUT_JSONL = "out/youtube.jsonl"
AUDIO_DIR = "out/audio"

def main():
    # Bước 1: Lấy URL từ trình duyệt
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
    
    # Bước 2: Thử lấy transcript
    print("[2/4] Đang thử lấy transcript từ YouTube...")
    try:
        rec = collect_youtube_transcript(
            url,
            languages=("vi", "en"),
            out_path=OUT_JSONL
        )
        print(f"✓ Đã lấy transcript thành công! ID: {rec.id}")
        print(f"✓ Text: {rec.text[:100]}..." if rec.text and len(rec.text) > 100 else f"✓ Text: {rec.text}")
        return
    except (NoTranscriptFound, TranscriptsDisabled) as e:
        print(f"⚠ Không lấy được transcript: {e}")
        print("→ Chuyển sang phương án tải audio và chuyển đổi sang text...\n")
    except Exception as e:
        print(f"⚠ Lỗi khi lấy transcript: {e}")
        print("→ Chuyển sang phương án tải audio và chuyển đổi sang text...\n")
    
    # Bước 3: Tải audio nếu không lấy được transcript
    print("[3/4] Đang tải audio từ YouTube...")
    try:
        # Lưu danh sách file hiện có trước khi tải
        existing_files = set()
        if os.path.exists(AUDIO_DIR):
            existing_files = {f for f in os.listdir(AUDIO_DIR) if os.path.isfile(os.path.join(AUDIO_DIR, f))}
        
        download_audio(url, outdir=AUDIO_DIR)
        
        # Tìm file mới nhất sau khi tải
        new_files = []
        if os.path.exists(AUDIO_DIR):
            for f in os.listdir(AUDIO_DIR):
                filepath = os.path.join(AUDIO_DIR, f)
                if os.path.isfile(filepath) and f not in existing_files:
                    new_files.append((filepath, os.path.getmtime(filepath)))
        
        if not new_files:
            # Nếu không tìm thấy file mới, lấy file mới nhất trong thư mục
            if os.path.exists(AUDIO_DIR):
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
    
    # Bước 4: Chuyển đổi audio sang text
    print("[4/4] Đang chuyển đổi audio sang text bằng STT...")
    try:
        # Đảm bảo file là WAV 16k mono
        wav_file = ensure_wav16k(audio_file)
        print(f"✓ Đã chuẩn hóa audio: {os.path.basename(wav_file)}")
        
        # Chạy STT
        stt_result = stt_vosk(wav_file)
        print(f"✓ Đã chuyển đổi sang text thành công")
        print(f"✓ Text: {stt_result['text'][:100]}..." if stt_result['text'] and len(stt_result['text']) > 100 else f"✓ Text: {stt_result['text']}")
        
        # Tạo record và lưu vào JSONL
        rec = build_record_from_file(audio_file, stt_result)
        append_jsonl(OUT_JSONL, rec)
        
        print(f"✓ Đã lưu kết quả vào {OUT_JSONL}")
        print(f"✓ Record ID: {rec.id}")
        
    except Exception as e:
        print(f"❌ Lỗi khi chuyển đổi audio sang text: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n✅ Hoàn thành!")

if __name__ == "__main__":
    main()