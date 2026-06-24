FROM python:3.13-slim

# ffmpeg is required by Whisper for audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the Whisper model so the container is ready without network access at runtime.
# Override WHISPER_MODEL at build time: docker build --build-arg WHISPER_MODEL=base .
ARG WHISPER_MODEL=small
RUN python -c "import whisper; whisper.load_model('${WHISPER_MODEL}')"

# Run as non-root to limit blast radius of any RCE vulnerability.
RUN useradd -m -u 1001 botuser \
    && mkdir -p /app/audio /app/logs \
    && chown -R botuser:botuser /app
USER botuser

CMD ["python", "main.py"]
