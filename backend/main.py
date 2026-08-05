from fastapi import FastAPI

app = FastAPI(title="Synapse API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
