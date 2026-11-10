# ClipGenius AI — backend starter

This is a **starter backend**, not a finished production service.

## Files
- `main.py` — FastAPI API for uploading a video, transcribing speech, adding subtitles, and downloading the result.
- `requirements.txt` — Python packages.

## Important limitations
- This starter currently processes the **whole uploaded video**; it does not yet find highlights or cut multiple short clips.
- It creates captions in the detected spoken language. Translation into other languages is not included yet.
- 1080p/4K output is a resolution setting; upscaling to 4K does not create extra source detail.
- Processing can be slow and memory-intensive on free CPU hosting.
- The service stores uploaded videos on its local disk. Some free hosts erase files when the service restarts.
- Do not deploy publicly as-is. Before public launch, add authentication, file-size limits, rate limits, secure storage, restricted CORS, and URL-fetch protections.

## Run locally
Install FFmpeg on the server, then run:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `/docs` on the running server to test the API.

## API
`POST /api/process`
- multipart file field: `video`
- optional query parameter: `quality=1080p` or `quality=4k`

`GET /api/download/{job_id}` downloads the processed MP4.
`GET /health` checks whether the API is running.

This starter accepts uploaded video files only. It does not download videos from social-media URLs.
