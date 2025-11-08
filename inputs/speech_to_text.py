# inputs/local_audio_stt_collector.py
# Quét thư mục audio -> (convert wav 16k mono nếu cần) -> STT (Vosk) -> append out/youtube.jsonl
# Chạy:
#   cd <project_root> && py -3.11 -m inputs.local_audio_stt_collector

from __future__ import annotations
import os, json, subprocess, wave, shutil
from typing import List, Optional, Dict, Any

# --- package-safe imports ---
try:
    from .schema import IngestRecord, Segment, append_jsonl
    from .utils import gen_id, now_iso
except ImportError:
    from schema import IngestRecord, Segment, append_jsonl
    from utils import gen_id, now_iso

OUT_JSONL_DEFAULT = "out/youtube.jsonl"
AUDIO_DIR_DEFAULT = "out/audio"
VOSK_MODEL = os.environ.get("VOSK_MODEL", "models/vosk-model-small-vn-0.4").strip()  # vd: models/vosk-model-small-vi-v0.22

SUPPORTED_EXTS = (".wav", ".mp3", ".m4a", ".aac", ".opus", ".flac", ".ogg")


# ---------- Helpers ----------
def list_audio_files(root: str, exts: tuple = SUPPORTED_EXTS) -> List[str]:
    files: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(exts):
                files.append(os.path.join(dirpath, name))
    return sorted(files)

def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def ensure_wav16k(input_path: str) -> str:
    """
    Trả về đường dẫn WAV mono 16k s16 tương ứng với input.
    Nếu input đã đúng chuẩn, trả về chính nó.
    Nếu không, dùng ffmpeg tạo file <stem>.stt.wav cạnh file gốc.
    """
    # Nếu đã là .wav, thử kiểm tra header xem đúng chuẩn chưa
    if input_path.lower().endswith(".wav"):
        try:
            with wave.open(input_path, "rb") as wf:
                if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == 16000:
                    return input_path
        except Exception:
            pass  # sẽ convert lại

    if not has_ffmpeg():
        raise RuntimeError("Cần FFmpeg trong PATH để convert audio về WAV 16k mono.")

    base, _ = os.path.splitext(input_path)
    out_wav = f"{base}.stt.wav"
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        out_wav
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_wav

def _load_vosk_model(model_dir: Optional[str]) :
    model_dir = model_dir or VOSK_MODEL
    if not model_dir:
        raise RuntimeError("Chưa cấu hình VOSK_MODEL (env) và chưa truyền model_dir.")
    if not os.path.isdir(model_dir):
        raise RuntimeError(f"Không tìm thấy thư mục Vosk model: {model_dir}")
    from vosk import Model
    return Model(model_dir)

def stt_vosk(wav_path: str, model_dir: Optional[str] = None) -> Dict[str, Any]:
    from vosk import KaldiRecognizer
    model = _load_vosk_model(model_dir)
    segments: List[Segment] = []

    with wave.open(wav_path, "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            raise RuntimeError("WAV phải là mono, 16-bit, 16kHz.")
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)

        def flush(res_json: str):
            if not res_json: return
            try:
                obj = json.loads(res_json)
            except Exception:
                return
            if "result" in obj and obj["result"]:
                words = obj["result"]
                start = words[0]["start"]
                end = words[-1]["end"]
                text = obj.get("text", "").strip()
                segments.append(Segment(start=float(start), duration=float(end - start), text=text))

        buf = 4000
        while True:
            data = wf.readframes(buf)
            if not data: break
            if rec.AcceptWaveform(data):
                flush(rec.Result())
            # else: rec.PartialResult()  # bỏ qua

        flush(rec.FinalResult())

    full_text = " ".join(seg.text for seg in segments if seg.text).strip()
    return {"text": full_text, "segments": segments}

def build_record_from_file(src_path: str, stt: Dict[str, Any]) -> IngestRecord:
    fname = os.path.basename(src_path)
    try:
        # tính duration nếu là wav
        dur = None
        if src_path.lower().endswith(".wav"):
            with wave.open(src_path, "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate())
    except Exception:
        dur = None

    rec = IngestRecord(
        id=gen_id("stt"),
        source_type="stt_local_audio",
        text=stt["text"],
        segments=stt["segments"],
        meta={
            "file_name": fname,
            "file_path": os.path.abspath(src_path),
            "duration": dur,
            "created_at": now_iso(),
            "engine": "vosk",
        },
    )
    return rec


# ---------- Batch ----------
def stt_from_folder(
    folder: str = AUDIO_DIR_DEFAULT,
    out_jsonl: str = OUT_JSONL_DEFAULT,
    model_dir: Optional[str] = None,
):
    os.makedirs(os.path.dirname(out_jsonl) or ".", exist_ok=True)
    files = list_audio_files(folder)
    if not files:
        print(f"Không tìm thấy audio trong: {folder}")
        return

    ok, fail = 0, 0
    print(f"Found {len(files)} file(s) in {folder}. Bắt đầu STT…")
    for path in files:
        try:
            wav = ensure_wav16k(path)
            stt = stt_vosk(wav, model_dir=model_dir)
            rec = build_record_from_file(path, stt)
            append_jsonl(out_jsonl, rec)
            print(f"[OK] {os.path.basename(path)} → id={rec.id}")
            ok += 1
        except Exception as e:
            print(f"[ERR] {os.path.basename(path)} → {e}")
            fail += 1
    print(f"==> DONE. OK={ok}, FAIL={fail}. Saved to {out_jsonl}")


# ---------- Interactive ----------
def main_interactive():
    folder = AUDIO_DIR_DEFAULT
    out_jsonl =  OUT_JSONL_DEFAULT
    model_dir =  None
    stt_from_folder(folder=folder, out_jsonl=out_jsonl, model_dir=model_dir)

if __name__ == "__main__":
    main_interactive()
