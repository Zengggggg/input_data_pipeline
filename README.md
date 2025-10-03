# Input Collectors

Repo này chứa các **collector đầu vào** phục vụ pipeline phân tích nội dung.  
**Nhiệm vụ của repo:** chuẩn hoá việc thu thập dữ liệu từ nhiều nguồn khác nhau (YouTube transcript, ảnh bình luận, audio hệ thống) thành **JSONL** thống nhất.<br>
**NOTE:** Video không có transcript(phụ đề) thì không lấy được ://


## 📂 Cấu trúc thư mục
```
input-data-pipline/
├─ common/ # code dùng chung (schema, utils)
│ ├─ schema.py # định nghĩa IngestRecord + hàm append_jsonl
│ └─ utils.py # tiện ích: gen_id, now_iso, youtube_id
│
├─ inputs/
│ └─ transcript_collector.py/ # collector lấy transcript YouTube
│
├─ out/ # thư mục output (JSONL + file nhị phân)
│ ├─ youtube.jsonl
│
├─ requirements.txt # thư viện Python cần thiết
└─ README.md
```


## 🛠 Cài đặt

Yêu cầu:
- Python 3.8+
- `ffmpeg` cài sẵn trong hệ thống (dùng cho audio collector)
Cài package Python:
```bash
pip install -r requirements.txt
```
## Cách chạy collector
1. YouTube Transcript

Lấy transcript từ video YouTube (ưu tiên ngôn ngữ vi, fallback en):
```bash
python -m inputs.youtube_transcript.collect "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --lang vi,en
```

Kết quả:

- File transcript được ghi vào `out/youtube.jsonl`

- Mỗi dòng là một JSON record (IngestRecord) với text và segments.
## 📦 Output chuẩn hóa

Mỗi collector đều xuất record theo schema IngestRecord trong common/schema.py. Ví dụ (JSONL một dòng):
```jsonl
{
  "id": "yt_123abc456def",
  "source_type": "youtube_transcript",
  "text": "đoạn transcript ...",
  "segments": [
    {"start": 0.0, "duration": 3.2, "text": "Xin chào"}
  ],
  "binary_path": null,
  "meta": {
    "video_id": "dQw4w9WgXcQ",
    "languages": ["vi","en"],
    "created_at": "2025-10-03T12:00:00Z"
  }
}
```
