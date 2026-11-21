"""mail-intake: receives inbound mail from the provider's webhook.

The mail provider posts each message that arrives for the support address as
raw MIME. This service parses it, keeps a short summary, and the support
inbox reads the summaries from here.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from . import __version__
from .config import load_settings
from .parsing import Summary, UnreadableMessage, summarise
from .store import Inbox

settings = load_settings()
inbox = Inbox(settings.keep)

app = FastAPI(title=settings.service_name, version=__version__)

ACCEPTED_TYPES = ("message/rfc822", "text/plain", "application/octet-stream")


class Message(BaseModel):
    id: int
    subject: str
    sender: str
    sender_name: str
    recipients: list[str]
    message_id: str
    sent_at: str | None
    hops: int
    last_hop: str | None
    attachments: list[str]
    preview: str


class MessageList(BaseModel):
    count: int
    messages: list[Message]


def _as_message(message_id: int, summary: Summary) -> Message:
    return Message(id=message_id, **asdict(summary))


@app.get("/health")
def health() -> dict:
    """Liveness probe. Also says which address this deployment collects for."""
    return {"status": "ok", "service": settings.service_name, "inbox": settings.inbox_address, "stored": len(inbox)}


@app.post("/inbound", response_model=Message, status_code=status.HTTP_201_CREATED)
async def inbound(request: Request) -> Message:
    """Accept one raw message from the mail provider and store its summary."""
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in ACCEPTED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "send the raw message as message/rfc822")
    raw = await request.body()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "the request has no message in it")
    if len(raw) > settings.max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"messages over {settings.max_bytes} bytes are not accepted")
    try:
        summary = summarise(raw)
    except UnreadableMessage as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    return _as_message(inbox.add(summary), summary)


@app.get("/messages", response_model=MessageList)
def list_messages(sender: str | None = None) -> MessageList:
    """Stored summaries, newest first. `sender` narrows the list to one address."""
    found = [_as_message(message_id, summary) for message_id, summary in inbox.newest_first(sender)]
    return MessageList(count=len(found), messages=found)


@app.get("/messages/{message_id}", response_model=Message)
def get_message(message_id: int) -> Message:
    summary = inbox.get(message_id)
    if summary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such message")
    return _as_message(message_id, summary)
