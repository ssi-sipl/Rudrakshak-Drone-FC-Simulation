# app.py

from contextlib import asynccontextmanager

from fastapi import FastAPI

from simulator import start_simulator


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Drone Simulator...")
    start_simulator()
    yield
    print("Stopping Drone Simulator...")


app = FastAPI(
    title="Drone Simulator API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "success": True,
        "message": "Drone Simulator Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }