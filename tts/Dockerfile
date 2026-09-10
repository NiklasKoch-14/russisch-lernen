FROM python:3.11-slim

ARG PIPER_VOICE=ru_RU-denis-medium
ARG PIPER_VOICE_FEMALE=ru_RU-irina-medium
ENV PIPER_VOICE=${PIPER_VOICE}
ENV PIPER_VOICE_FEMALE=${PIPER_VOICE_FEMALE}
ENV PIPER_MODEL_DIR=/models

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Modelle beim Bauen holen: kein Erstlauf-Download, laeuft danach ohne Internet.
# Zwei Stimmen, damit in den Hoergespraechen zwei Figuren zu unterscheiden sind.
RUN mkdir -p /models \
 && python3 -m piper.download_voices ${PIPER_VOICE} --data-dir /models \
 && python3 -m piper.download_voices ${PIPER_VOICE_FEMALE} --data-dir /models

COPY app.py .

EXPOSE 5001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]
