from arq.connections import RedisSettings
from database import db, settings
from deployer import run_deploy

async def startup(ctx: dict):
    await db.connect()

async def shutdown(ctx:dict):
    await db.disconnect()

class WorkerSettings():
    functions = [run_deploy]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = settings.arq_redis_settings
    max_tries = 3
    retry_jobs = True
    job_timeout = 300        # 5 min max per deploy
    keep_result = 3600       # keep result in Redis for 1 hour

