import uvicorn

from contextlib import asynccontextmanager
from fastapi import FastAPI

from database import engine
from routers import ping


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.include_router(ping.router, prefix="/api/v1")  # Health check endpoint

if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")

