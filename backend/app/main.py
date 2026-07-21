from fastapi import FastAPI

app = FastAPI(title="Speaker Backend")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
