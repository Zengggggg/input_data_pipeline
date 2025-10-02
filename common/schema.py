from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import json, pathlib

class Segment(BaseModel):
    start: float
    duration: float
    text: str

class IngestRecord(BaseModel):
    id: str
    source_type: str
    text: Optional[str] = None
    segments: Optional[List[Segment]] = None
    binary_path: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

def append_jsonl(path: str, record: IngestRecord):
    """Ghi 1 dòng JSON (UTF-8, không escape unicode) – tương thích Pydantic v1/v2."""
    # Lấy dict từ model (v2: model_dump, v1: dict)
    try:
        data = record.model_dump()
    except AttributeError:   # Pydantic v1
        data = record.dict()

    line = json.dumps(data, ensure_ascii=False)
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
