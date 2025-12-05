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
    """Write a JSONL line. Works for Pydantic v1 & v2."""
    
    # Convert Pydantic model → dict
    try:
        data = record.model_dump()      # Pydantic v2
    except AttributeError:
        data = record.dict()            # Pydantic v1

    line = json.dumps(data, ensure_ascii=False)
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
