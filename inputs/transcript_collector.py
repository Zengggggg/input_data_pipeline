# inputs/transcript_collector.py
from typing import List, Sequence, Optional, Iterable
import os
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

try:
    from .schema import IngestRecord, Segment, append_jsonl
    from .utils import youtube_id, gen_id, now_iso
except ImportError:
    from schema import IngestRecord, Segment, append_jsonl
    from utils import youtube_id, gen_id, now_iso


def collect_youtube_transcript(
    video: str,
    languages: Sequence[str] = ("vi", "en"),
    out_path: Optional[str] = "out/youtube.jsonl",
) -> IngestRecord:
    vid = youtube_id(video)
    if not vid:
        raise ValueError("Không tìm thấy video ID từ đầu vào")

    langs: List[str] = [x.strip() for x in languages if str(x).strip()] or ["vi", "en"]

    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(vid, languages=langs)
    raw = transcript.to_raw_data()

    rec = IngestRecord(
        id=gen_id("yt"),
        source_type="youtube_transcript",
        text="\n".join(x["text"] for x in raw).strip(),
        segments=[Segment(start=x["start"], duration=x["duration"], text=x["text"]) for x in raw],
        meta={"video_id": vid, "created_at": now_iso(), "languages": langs},
    )

    if out_path:
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        append_jsonl(out_path, rec)

    return rec



def collect_batch(
    urls: Iterable[str],
    languages: Sequence[str] = ("vi", "en"),
    out_path: str = "out/youtube.jsonl",
):
    """Thu thập transcript cho nhiều URL; ghi append vào out_path, in kết quả từng URL."""
    ok, fail = 0, 0
    for url in urls:
        try:
            rec = collect_youtube_transcript(url, languages, out_path)
            print(f"[OK] {url}  → id={rec.id}")
            ok += 1
        except TranscriptsDisabled:
            print(f"[SKIP] Tắt transcript: {url}")
            fail += 1
        except NoTranscriptFound:
            print(f"[SKIP] Không có transcript theo ngôn ngữ: {url}")
            fail += 1
        except Exception as e:
            print(f"[ERR] {url} → {e}")
            fail += 1
    print(f"==> Done. OK={ok}, FAIL={fail}. Saved to {out_path}")


def main_interactive():
    langs = "vi,en"
    out_path = "out/youtube.jsonl"

    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
    ]

    languages = [x.strip() for x in langs.split(",") if x.strip()]
    collect_batch(urls, languages, out_path)


if __name__ == "__main__":
    # Chạy:  cd <project_root> ; py -3.11 -m inputs.transcript_collector
    main_interactive()
