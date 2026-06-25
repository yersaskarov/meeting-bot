FROM python:3.13-slim

# ffmpeg is required by Whisper for audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the Whisper model into a fixed path accessible to all users.
# Without WHISPER_CACHE, the model would be stored in /root/.cache at build time
# but looked up in /home/botuser/.cache at runtime (different user), causing a
# re-download on every container start.
ARG WHISPER_MODEL=small
ENV WHISPER_CACHE=/app/.cache/whisper
RUN mkdir -p /app/.cache/whisper && \
    python -c "import whisper; whisper.load_model('${WHISPER_MODEL}', download_root='/app/.cache/whisper')"

# Run as non-root to limit blast radius of any RCE vulnerability.
RUN useradd -m -u 1001 botuser \
    && mkdir -p /app/audio /app/logs /app/data \
    && chown -R botuser:botuser /app
USER botuser

CMD ["python", "main.py"]
