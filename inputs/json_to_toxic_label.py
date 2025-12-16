import json
import re

# Đọc transcript từ file JSON
with open('out/last_run.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
transcript = data['transcript']

# Tách câu dựa vào dấu chấm, hỏi, cảm thán
sentences = re.split(r'(?<=[.!?])\s+', transcript.strip())
sentences = [s for s in sentences if s.strip()]

# Tạo danh sách gán nhãn (toxic mặc định là False, chỉnh lại sau)
result = [{"sentence": s, "toxic": False} for s in sentences]

# Ghi ra file mới
with open('out/transcript_toxic_labeled.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Đã tạo file out/transcript_toxic_labeled.json. Hãy mở file này để gán nhãn toxic cho từng câu.")
