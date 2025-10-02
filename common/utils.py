import re, time, uuid
from typing import Optional  # <— thêm


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

_YT_PATTERNS = [
    r"(?:v=|vi=)([A-Za-z0-9_-]{11})",
    r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
    r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
    r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
]

def youtube_id(s: str) -> Optional[str]:
    s = s.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", s): return s
    for pat in _YT_PATTERNS:
        m = re.search(pat, s)
        if m: return m.group(1)
    return None
