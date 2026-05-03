from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import db
from routers.webhooks import router as webhooks_router
from routers.deployments import router as deployments_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(title="Webhook Platform",lifespan=lifespan)
app.include_router(webhooks_router)
app.include_router(deployments_router)
@app.get("/health")
async def health_check():
    return {"status":"ok"}
