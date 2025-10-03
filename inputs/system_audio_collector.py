# Usage (PowerShell):
#   python -m inputs.system_audio_collector --model "C:\models\vosk-model-small-vn-0.4" --sec 8
#   python -m inputs.system_audio_collector --model "C:\models\vosk-model-small-en-us-0.15" --device "CABLE Output (VB-Audio Virtual Cable)" --sec 10

import argparse
import pathlib
import subprocess
import wave
import json
from vosk import Model, KaldiRecognizer

from common.schema import IngestRecord, Segment, append_jsonl
from common.utils import gen_id, now_iso

def record_with_ffmpeg(device_name: str, outwav: str, sec: int):
    """Ghi âm system audio từ thiết bị DirectShow bằng FFmpeg."""
    pathlib.Path(outwav).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "dshow",
        "-i", f"audio={device_name}",
        "-t", str(sec),
        "-ac", "1",        # mix mono cho Vosk
        "-ar", "16000",    # Vosk chạy tốt ở 16kHz
        outwav
    ]
    subprocess.run(cmd, check=True)

def asr_vosk(wav_path: str, model_path: str):
    """Nhận diện giọng nói bằng Vosk, trả transcript + segments."""
    wf = wave.open(wav_path, "rb")
    model = Model(model_path)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    text_parts = []
    segments = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            r = json.loads(rec.Result())
            if r.get("text"):
                text_parts.append(r["text"])
            if "result" in r:
                words = r["result"]
                if words:
                    seg_text = r.get("text", "").strip()
                    start = float(words[0]["start"])
                    end = float(words[-1]["end"])
                    if seg_text:
                        segments.append(Segment(start=start, duration=end - start, text=seg_text))
    r_final = json.loads(rec.FinalResult())
    if r_final.get("text"):
        text_parts.append(r_final["text"])
        words = r_final.get("result") or []
        if words:
            seg_text = r_final.get("text", "").strip()
            start = float(words[0]["start"])
            end = float(words[-1]["end"])
            if seg_text:
                segments.append(Segment(start=start, duration=end - start, text=seg_text))

    return " ".join(text_parts).strip(), segments

def main():
    ap = argparse.ArgumentParser(description="Record system audio with FFmpeg + transcribe with Vosk")
    ap.add_argument("--model", required=True, help="Đường dẫn tới thư mục model Vosk")
    ap.add_argument("--sec", type=int, default=8, help="Số giây cần ghi")
    ap.add_argument("--device", default="CABLE Output (VB-Audio Virtual Cable)", help="Tên thiết bị DirectShow audio")
    ap.add_argument("--outdir", default="out/audio", help="Thư mục lưu WAV")
    ap.add_argument("--metaout", default="out/audio.jsonl", help="File JSONL output")
    args = ap.parse_args()

    pathlib.Path(args.outdir).mkdir(parents=True, exist_ok=True)
    wav_path = f"{args.outdir}/{gen_id('aud')}.wav"

    # Ghi âm bằng ffmpeg
    record_with_ffmpeg(args.device, wav_path, args.sec)

    # ASR bằng Vosk
    text, segments = asr_vosk(wav_path, args.model)

    # Build record theo schema
    rec = IngestRecord(
        id=pathlib.Path(wav_path).stem,
        source_type="system_audio",
        text=text if text else None,
        segments=segments if segments else None,
        binary_path=wav_path,
        meta={
            "device": args.device,
            "sec": args.sec,
            "sr": 16000,
            "channels": 1,
            "created_at": now_iso(),
            "engine": "vosk"
        }
    )

    append_jsonl(args.metaout, rec)
    print(f"WAV: {wav_path}")
    print(f"JSONL: {args.metaout}")
    if not text:
        print("⚠️ Không nhận được lời nói (im lặng hoặc chỉ có nhạc).")

if __name__ == "__main__":
    main()
