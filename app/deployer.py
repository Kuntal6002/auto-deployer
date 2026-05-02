import asyncio
import asyncssh
from typing import AsyncIterator
from database import db


async def _stream_ssh(host: str, user: str, command: str) -> AsyncIterator[str]:
    """Yield stdout lines from an SSH command, one at a time."""
    async with asyncssh.connect(
        host,
        username=user,
        known_hosts=None,         # TODO: pin known_hosts in production
    ) as conn:
        async with conn.create_process(command) as proc:
            async for line in proc.stdout:
                yield line.rstrip("\n")
            await proc.wait()
            if proc.exit_status != 0:
                raise RuntimeError(f"Remote command failed (exit {proc.exit_status})")


async def run_deploy(ctx: dict, *, deployment_id: int, host: str, user: str, workdir: str):
    """
    arq job — called by the worker.
    Streams deploy output line-by-line into deployment_logs.
    """
    await db.execute(
        "UPDATE deployments SET status='running', started_at=NOW() WHERE id=$1",
        deployment_id,
    )

    command = (
        f"cd {workdir} "
        "&& docker compose pull --quiet "
        "&& docker compose up -d --remove-orphans "
        "&& docker compose ps"
    )

    log_seq = 0
    try:
        async for line in _stream_ssh(host, user, command):
            await db.execute(
                "INSERT INTO deployment_logs (deployment_id, seq, line) VALUES ($1, $2, $3)",
                deployment_id, log_seq, line,
            )
            log_seq += 1

        await db.execute(
            "UPDATE deployments SET status='success', finished_at=NOW() WHERE id=$1",
            deployment_id,
        )

    except Exception as exc:
        await db.execute(
            "INSERT INTO deployment_logs (deployment_id, seq, line) VALUES ($1, $2, $3)",
            deployment_id, log_seq, f"ERROR: {exc}",
        )
        await db.execute(
            "UPDATE deployments SET status='failed', finished_at=NOW() WHERE id=$1",
            deployment_id,
        )
        raise  # re-raise so arq records the failure and can retry
