import os
import uuid
from datetime import datetime
from pydub import AudioSegment
from google.cloud import speech_v1p1beta1 as speech
from inputs.schema import IngestRecord
import pathlib
from dotenv import load_dotenv

load_dotenv()

# Kiểm tra biến môi trường
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS in .env")


# ----------------------------------------------------
# 1) Chuẩn hóa audio về WAV 16kHz mono
# ----------------------------------------------------
def ensure_wav16k(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".wav":
            audio = AudioSegment.from_wav(path)
            if audio.frame_rate == 16000 and audio.channels == 1:
                return path
    except:
        pass

    audio = AudioSegment.from_file(path)
    audio = audio.set_frame_rate(16000).set_channels(1)

    out_path = path.rsplit(".", 1)[0] + "_16k.wav"
    audio.export(out_path, format="wav")
    return out_path


# ----------------------------------------------------
# 2) Chia audio theo thời gian (đảm bảo < 1 phút)
# ----------------------------------------------------
def split_audio_chunks(wav_file: str, chunk_ms: int = 50000) -> list[str]:
    """
    Chia audio thành các file WAV dài tối đa chunk_ms.
    chunk_ms = 50000ms = 50s < 60s (Google STT Sync limit)
    """
    audio = AudioSegment.from_wav(wav_file)
    chunks = []

    duration = len(audio)
    index = 0

    while index < duration:
        chunk = audio[index:index + chunk_ms]
        chunk_path = f"{wav_file.rsplit('.',1)[0]}_chunk{len(chunks)}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)
        index += chunk_ms

    return chunks


# ----------------------------------------------------
# 3) Google STT (sync) → text
# ----------------------------------------------------
def speech_to_text_from_file(wav_file: str) -> dict:
    client = speech.SpeechClient()
    full_text = ""

    # LUÔN chia theo thời gian, không chia theo dung lượng file
    chunks = split_audio_chunks(wav_file)

    for idx, chunk_path in enumerate(chunks, 1):
        print(f"[chunk {idx}/{len(chunks)}] Đang STT: {os.path.basename(chunk_path)}")

        try:
            with open(chunk_path, "rb") as f:
                audio_content = f.read()

            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="vi-VN",
                enable_automatic_punctuation=True,
            )

            response = client.recognize(config=config, audio=audio)

            text_chunk = " ".join([r.alternatives[0].transcript for r in response.results])
            full_text += " " + text_chunk

        except Exception as e:
            print("❌ Lỗi chunk:", e)

        finally:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

    return {"text": full_text.strip()}


# ----------------------------------------------------
# 4) Build record để lưu JSONL
# ----------------------------------------------------
def build_record_from_file(audio_path: str, stt_result):
    print("STT RAW:", stt_result, type(stt_result))  # ❗ Debug

    # Nếu stt_result là dict
    if isinstance(stt_result, dict):
        # trường hợp bị lồng dict {'text': {'text': 'Cũng được.'}}
        if isinstance(stt_result.get("text"), dict):
            text = stt_result["text"].get("text", "")
        else:
            text = stt_result.get("text", "")

    # Nếu là string → parse bằng ast
    else:
        import ast
        stt_dict = ast.literal_eval(stt_result)
        text = stt_dict.get("text", "")

    return IngestRecord(
        id=str(pathlib.Path(audio_path).stem),
        source_type="audio",
        text=text,
        binary_path=str(audio_path),
        segments=None,
        meta={}
    )
