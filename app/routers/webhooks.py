import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from database import db, settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(body: bytes, sig_header: str | None) -> None:
    if not settings.github_webhook_secret:
        return
    """Verify GitHub's X-Hub-Signature-256 header."""
    if not sig_header or not sig_header.startswith("sha256="):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


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

    row = await db.execute(
        """
        INSERT INTO webhook_events (event_type, action, repo, sender, payload)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        x_github_event,
        action,
        repo,
        sender,
        json.dumps(payload),
    )

    return {"status": "accepted", "event": x_github_event, "repo": repo}


@router.get("/github")
async def list_events(limit: int = 50) -> list[dict[str, Any]]:
    rows = await db.fetch(
        "SELECT id, event_type, action, repo, sender, created_at FROM webhook_events ORDER BY created_at DESC LIMIT $1",
        limit,
    )
    return [dict(r) for r in rows]
