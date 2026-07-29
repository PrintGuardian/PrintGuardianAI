from fastapi import FastAPI

app = FastAPI(title="PrintGuardianAI")

@app.get("/")
def health_check():
    return {"status": "running", "service": "PrintGuardianAI"}

@app.get("/api/status")
def status():
    return {"ai": "offline", "camera": "not_connected"}
