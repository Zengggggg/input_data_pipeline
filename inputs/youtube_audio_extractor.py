import os
from typing import Iterable, Union
import yt_dlp

OUTDIR = os.path.join("out", "audio")

def _progress_hook(d):
    if d.get('status') == 'downloading':
        p = d.get('_percent_str', '').strip()
        s = d.get('_speed_str', '').strip()
        eta = d.get('eta')
        eta_str = f"{eta//60:02d}:{eta%60:02d}" if isinstance(eta, int) else "??:??"
        print(f"[DOWN] {p} at {s} ETA {eta_str}", end="\r")
    elif d.get('status') == 'finished':
        print("\n[POST] Converting to audio…")

def download_audio(
    urls: Union[str, Iterable[str]],
    outdir: str = OUTDIR,
    codec: str = "mp3",          # "mp3" | "m4a" | "opus" | "mp2" | "wav" | ...
    bitrate_kbps: int = 192,
    sample_rate: int = 44100,
    allow_playlist: bool = True,
):
    if isinstance(urls, str):
        urls = [urls]
    os.makedirs(outdir, exist_ok=True)

    # Ưu tiên m4a cho YouTube (tránh 403 ở opus/251), fallback về bestaudio.
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(outdir, "%(title).200B-%(id)s.%(ext)s"),
        "noplaylist": not allow_playlist,
        "ignoreerrors": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragments": 5,
        "prefer_ffmpeg": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": codec,
            "preferredquality": str(bitrate_kbps),
        }],
        "postprocessor_args": ["-ar", str(sample_rate)],
        "progress_hooks": [_progress_hook],
        "windowsfilenames": True,
        "overwrites": False,
        "quiet": False,
        "no_warnings": False,
        # Tránh lỗi random: giả lập Android client cho YouTube, headers cơ bản, IPv4
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "http_headers": {"User-Agent": "Mozilla/5.0", "Referer": "https://www.google.com"},
        "force_ipv4": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(list(urls))

if __name__ == "__main__":
    # Ví dụ: một URL YouTube
    download_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    # Ví dụ: Facebook (tự nhận bestaudio; nếu muốn MP2 thì đổi codec="mp2")
    # download_audio("https://www.facebook.com/share/v/17bRENMeDQ/", codec="mp2")
