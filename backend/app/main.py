from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine, Base
from .routes import ingest as r_ingest, ask as r_ask

app = FastAPI(title="Titan-Guidance API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(r_ingest.router)
app.include_router(r_ask.router)

@app.get("/")
def health():
    return {"ok": True}
