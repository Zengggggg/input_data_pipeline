# usage:
#   python -m inputs.transcript_collector "{youtue-url}" --lang vi,en
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from argparse import ArgumentParser
from common.schema import IngestRecord, Segment, append_jsonl
from common.utils import youtube_id, gen_id, now_iso

def main():
    ap = ArgumentParser()
    ap.add_argument("video", help="YouTube URL hoặc ID")
    ap.add_argument("--lang", default="vi,en", help="Danh sách ngôn ngữ ưu tiên, ví dụ: vi,en")
    ap.add_argument("--out", default="out/youtube.jsonl")
    args = ap.parse_args()

    vid = youtube_id(args.video)
    if not vid: raise SystemExit("Không tìm thấy video ID")

    ytt = YouTubeTranscriptApi()
    langs = [x.strip() for x in args.lang.split(",") if x.strip()]
    ft = ytt.fetch(vid, languages=langs)
    raw = ft.to_raw_data()  # [{'text','start','duration'}, ...]

    rec = IngestRecord(
        id=gen_id("yt"),
        source_type="youtube_transcript",
        text="\n".join(x["text"] for x in raw).strip(),
        segments=[Segment(start=x["start"], duration=x["duration"], text=x["text"]) for x in raw],
        meta={"video_id": vid, "created_at": now_iso(), "languages": langs}
    )
    append_jsonl(args.out, rec)
    print(f" saved → {args.out} (id={rec.id})")

if __name__ == "__main__":
    try: main()
    except TranscriptsDisabled: print("Video tắt transcript")
    except NoTranscriptFound:   print("Không có transcript cho ngôn ngữ yêu cầu")
