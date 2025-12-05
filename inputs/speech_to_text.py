import os
import uuid
import subprocess
from datetime import datetime
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from inputs.schema import IngestRecord



# ================================
# 1. Chuẩn hóa file WAV 16kHz
# ================================
def ensure_wav16k(input_path: str) -> str:
    """
    Convert any audio file to 16kHz WAV mono.
    """
    output_path = input_path.rsplit(".", 1)[0] + "_16k.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", "16000",
        output_path
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


# ================================
# 2. Upload file lên Google Cloud Storage
# ================================
def upload_to_gcs(local_path: str, bucket_name: str) -> str:
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob_name = f"audio/{uuid.uuid4()}.wav"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)

    return f"gs://{bucket_name}/{blob_name}"


# ================================
# 3. Google STT — Speech-to-Text từ đường dẫn GCS
# ================================
def speech_to_text_from_file(local_wav_path: str) -> str:
    """
    Upload file lên GCS → Gọi Google STT → Trả về text
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME is not set in environment variables.")

    gcs_uri = upload_to_gcs(local_wav_path, bucket_name)

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="vi-VN",
        enable_automatic_punctuation=True,
        model="default"
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result()

    text = ""
    for result in response.results:
        text += result.alternatives[0].transcript + " "

    return text.strip()


# ================================
# 4. Build schema record
# ================================


def build_record_from_file(video_id: str, audio_local_path: str, text: str) -> IngestRecord:
    """
    Trả về 1 IngestRecord Pydantic model (KHÔNG trả về dict).
    """
    return IngestRecord(
        id=video_id,
        source_type="youtube",
        text=text,
        segments=None,
        binary_path=audio_local_path,
        meta={
            "provider": "google_speech_to_text",
            "language": "vi-VN"
        }
    )

