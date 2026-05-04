import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from arq import create_pool

from database import db, settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(body: bytes, sig_header: str | None) -> None:
    if not settings.github_webhook_secret:
        return
    """Verify GitHub's X-Hub-Signature-256 header."""
    if not sig_header or not sig_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature"
        )

    expected = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def receive_github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: str | None = Header(None),
) -> dict[str, Any]:
    body = await request.body()
    verify_signature(body, x_hub_signature_256)

    payload: dict[str, Any] = await request.json()
    action = payload.get("action")
    repo = payload.get("repository", {}).get("full_name")
    sender = payload.get("sender", {}).get("login")

    await db.execute(
        "INSERT INTO webhook_events (event_type, action, repo, sender, payload) VALUES ($1,$2,$3,$4,$5)",
        x_github_event,
        action,
        repo,
        sender,
        json.dumps(payload),
    )

    if x_github_event == "push" and repo:
        # Look up projects config with this repo
        project = project = await db.fetchrow(
            "SELECT id, deploy_host, deploy_user, deploy_workdir FROM projects WHERE repo = $1",
            repo,
        )
        if project:
            row = await db.fetchrow(
                "INSERT INTO deployments (project_id, repo, triggered_by) VALUES ($1,$2,$3) RETURNING id",
                project["id"],
                repo,
                sender,
            )
            deployment_id = row["id"]

            redis = await create_pool(settings.arq_redis_settings)
            await redis.enqueue_job(
                "run_deploy",
                deployment_id=deployment_id,
                host=project["deploy_host"],
                user=project["deploy_user"],
                workdir=project["deploy_workdir"],
                _job_id=f"deploy:{repo}:{deployment_id}",  # dedupe key
            )

            await redis.close()

            return {
                "status": "accepted",
                "event": x_github_event,
                "deployment_id": deployment_id,
            }
    return {"status": "accepted", "event": x_github_event, "queued": "False"}


@router.get("/github")
async def list_events(limit: int = 50) -> list[dict[str, Any]]:
    rows = await db.fetch(
        "SELECT id, event_type, action, repo, sender, created_at FROM webhook_events ORDER BY created_at DESC LIMIT $1",
        limit,
    )
    return [dict(r) for r in rows]
