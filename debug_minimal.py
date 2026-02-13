# Minimal Debug App
import os
import sys
from fastapi import FastAPI
import uvicorn

print("🔥 MINIMAL DEBUG APP STARTING 🔥", file=sys.stderr)

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "Minimal debug app is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
