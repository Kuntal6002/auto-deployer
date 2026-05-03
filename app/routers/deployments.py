import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database import db

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get("")
async def list_deployments(limit: int = 20) -> list[dict[str, Any]]:
    rows = await db.fetch(
        """
        SELECT id, repo, status, triggered_by, triggered_at, started_at, finished_at
        FROM deployments ORDER BY triggered_at DESC LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


@router.get("/{deployment_id}")
async def get_deployment(deployment_id: int) -> dict[str, Any]:
    row = await db.fetchrow("SELECT * FROM deployments WHERE id=$1", deployment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return dict(row)


@router.get("/{deployment_id}/logs")
async def get_logs(deployment_id: int) -> list[dict[str, Any]]:
    rows = await db.fetch(
        "SELECT seq, line, created_at FROM deployment_logs WHERE deployment_id=$1 ORDER BY seq",
        deployment_id,
    )
    return [dict(r) for r in rows]


async def _sse_log_stream(deployment_id: int) -> AsyncIterator[str]:
    last_seq = -1
    terminal = {"success", "failed", "cancelled"}

    while True:
        rows = await db.fetch(
            "SELECT seq, line FROM deployment_logs WHERE deployment_id=$1 AND seq > $2 ORDER BY seq",
            deployment_id, last_seq,
        )
        for row in rows:
            last_seq = row["seq"]
            data = json.dumps({"seq": row["seq"], "line": row["line"]})
            yield f"data: {data}\n\n"

        dep = await db.fetchrow(
            "SELECT status FROM deployments WHERE id=$1", deployment_id
        )
        if dep and dep["status"] in terminal and not rows:
            yield f"event: done\ndata: {json.dumps({'status': dep['status']})}\n\n"
            break

        await asyncio.sleep(0.5)


@router.get("/{deployment_id}/stream")
async def stream_logs(deployment_id: int):
    dep = await db.fetchrow("SELECT id FROM deployments WHERE id=$1", deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return StreamingResponse(
        _sse_log_stream(deployment_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
