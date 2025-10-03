# Input Collectors

Repo này chứa các **collector đầu vào** phục vụ pipeline phân tích nội dung.  
**Nhiệm vụ của repo:** chuẩn hoá việc thu thập dữ liệu từ nhiều nguồn khác nhau (YouTube transcript, ảnh bình luận, audio hệ thống) thành **JSONL** thống nhất.<br>
**NOTE:** Video không có transcript(phụ đề) thì không lấy được ://


## 📂 Cấu trúc thư mục
```
input-data-pipeline/
├─ common/ # code dùng chung (schema, utils)
│ ├─ schema.py # định nghĩa IngestRecord + hàm append_jsonl
│ └─ utils.py # tiện ích: gen_id, now_iso, youtube_id
│
├─ inputs/
│ ├─ youtube_transcript.py # collector lấy transcript YouTube
│ └─ system_audio_collector.py # collector lấy audio từ hệ thống và thực hiện speech2text
│
├─ out/ # thư mục output (JSONL + file nhị phân)
│ ├─ youtube.jsonl
│ ├─ audio.jsonl
│ └─ audio/
|       └─audio.waw # các audio thu thập được từ hệ thống
│
├─ requirements.txt # thư viện Python cần thiết
└─ README.md
```


## 🛠 Cài đặt

Yêu cầu:
- Python 3.8+
- `ffmpeg` cài sẵn trong hệ thống (dùng cho audio collector)
- Với **system audio collector**: cần **VB-Audio Virtual Cable** để route âm thanh hệ thống
Cài package Python:
```bash
pip install -r requirements.txt
```
Cài VB-CABLE (cho system audio):

1. [Tải VB-Audio Cable](https://vb-audio.com/Cable/)

2. Cài đặt và khởi động lại máy.
3. Để đảm bảo đã cài đặt thành công vào Control Panel -> Hardware and Sound -> Sound <br>
   Nếu trong Playback hiện ra thiết bị CABLE Input và Recording hiện ra CABLE Ouput

4. Trong Windows Sound Settings, chọn CABLE Input làm output cho app hoặc toàn hệ thống.
   Collector sẽ thu từ CABLE Output.
   
Tải mô hình Vosk
Tải mô hình tiếng Việt và giải nén vào `C:\models`
```powershell
New-Item -ItemType Directory -Force C:\models | Out-Null

Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip" -OutFile "$env:TEMP\vosk-vn.zip"

Expand-Archive "$env:TEMP\vosk-vn.zip" "C:\models" -Force
```
Sau khi chạy, bạn sẽ có thư mục:
```makefile
C:\models\vosk-model-small-vn-0.4\

```
Nếu cần tiếng Anh (US):
```powershell
New-Item -ItemType Directory -Force C:\models | Out-Null

Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip" -OutFile "$env:TEMP\vosk-en.zip"

Expand-Archive "$env:TEMP\vosk-en.zip" "C:\models" -Force
```
Kết quả:
```makefile
C:\models\vosk-model-small-en-us-0.15\
```
## Cách chạy collector
1. YouTube Transcript

Lấy transcript từ video YouTube (ưu tiên ngôn ngữ vi, fallback en):
```bash
python -m inputs.transcript_collector "{youtue-url}" --lang vi,en
```
2. System Audio (FFmpeg + Vosk)
Thu và nhận diện âm thanh hệ thống (qua VB-CABLE + FFmpeg + Vosk):
Ví dụ thu 8 giây tiếng Việt:
```powershell
python -m inputs.system_audio_collector --model "C:\models\vosk-model-small-vn-0.4" --sec 8
```
Kết quả:

- File WAV: out/audio/aud_xxx.wav

- File JSONL transcript: out/audio.jsonl

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

