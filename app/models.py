from pydantic import BaseModel
from typing import Any

class WebhookEvent(BaseModel):
    id:str
    event_type: str
    action: str | None
    repo: str | None
    sender: str | None
    payload:dict[str,Any]
    created_at:str
