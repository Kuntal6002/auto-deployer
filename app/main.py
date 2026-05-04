from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import db
from routers.webhooks import router as webhooks_router
from routers.deployments import router as deployments_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(title="Webhook Platform",lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
Instrumentator().instrument(app).expose(app)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(webhooks_router)
app.include_router(deployments_router)
@app.get("/health")
async def health_check():
    return {"status":"ok"}

