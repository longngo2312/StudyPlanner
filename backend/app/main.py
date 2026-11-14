#app/main.py
#entrypoint for the app (includes FastAPI app, CORS middleware, and API routes)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routes import plan

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Study Planner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  #vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plan.router)

@app.get("/health")
def health():
    return {"status": "ok"}