FROM python:3.11-slim

ARG PIPER_VOICE=ru_RU-dmitri-medium
ENV PIPER_VOICE=${PIPER_VOICE}
ENV PIPER_MODEL_PATH=/models/${PIPER_VOICE}.onnx

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Modell beim Bauen holen: kein Erstlauf-Download, laeuft danach ohne Internet.
RUN mkdir -p /models \
 && python3 -m piper.download_voices ${PIPER_VOICE} --data-dir /models

COPY app.py .

EXPOSE 5001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]
