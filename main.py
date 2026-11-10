import os
import shutil
import uuid
import subprocess
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel

ROOT = Path(__file__).parent
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)

app = FastAPI(title="ClipGenius AI API")

# Development CORS only. Restrict this to your website's domain before public launch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None

def get_model():
    global _model
    if _model is None:
        # CPU-friendly starter model. First run downloads model files.
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model

def run_ffmpeg(args):
    result = subprocess.run(
        ["ffmpeg", "-y", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])

def srt_time(seconds):
    ms = int(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

@app.get("/")
def home():
    return {
        "name": "ClipGenius AI",
        "status": "backend online",
        "note": "Upload a video to /api/process"
    }

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/process")
async def process_video(video: UploadFile = File(...), quality: str = "1080p"):
    if not video.filename:
        raise HTTPException(400, "Please choose a video file.")
    suffix = Path(video.filename).suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}:
        raise HTTPException(400, "Unsupported video format.")

    job_id = str(uuid.uuid4())
    job_dir = WORK / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_path = job_dir / f"input{suffix}"
    audio_path = job_dir / "audio.wav"
    srt_path = job_dir / "captions.srt"
    output_path = job_dir / "clipgenius_output.mp4"

    try:
        with input_path.open("wb") as out:
            shutil.copyfileobj(video.file, out)

        run_ffmpeg(["-i", str(input_path), "-vn", "-ac", "1", "-ar", "16000", str(audio_path)])

        model = get_model()
        segments, info = model.transcribe(str(audio_path), vad_filter=True)

        srt_lines = []
        for index, segment in enumerate(segments, start=1):
            srt_lines.extend([
                str(index),
                f"{srt_time(segment.start)} --> {srt_time(segment.end)}",
                segment.text.strip(),
                ""
            ])
        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

        # This starter exports the complete video with readable subtitles.
        # It does not yet perform AI highlight selection or translation.
        scale = "scale=-2:1080" if quality.lower() == "1080p" else "scale=-2:2160"
        escaped_srt = str(srt_path).replace("\\", "/").replace(":", r"\:")
        run_ffmpeg([
            "-i", str(input_path),
            "-vf", f"{scale},subtitles='{escaped_srt}'",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            str(output_path)
        ])

        return {
            "job_id": job_id,
            "status": "completed",
            "detected_language": info.language,
            "download_url": f"/api/download/{job_id}",
            "message": "Video processed with speech captions."
        }
    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(500, f"Processing failed: {exc}")
    finally:
        await video.close()

@app.get("/api/download/{job_id}")
def download(job_id: str):
    path = WORK / job_id / "clipgenius_output.mp4"
    if not path.exists():
        raise HTTPException(404, "Output not found. Process a video first.")
    return FileResponse(path, media_type="video/mp4", filename="clipgenius_output.mp4")
