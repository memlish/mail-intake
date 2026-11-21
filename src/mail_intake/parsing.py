"""Turn a raw message from the mail provider into the summary the inbox shows."""

from __future__ import annotations

from dataclasses import dataclass, field

import mailparser
from mailparser.exceptions import MailParserError

PREVIEW_CHARS = 200


class UnreadableMessage(ValueError):
    """The bytes could not be read as a mail message the inbox can use."""


@dataclass(frozen=True)
class Summary:
    subject: str
    sender: str
    sender_name: str
    recipients: list[str]
    message_id: str
    sent_at: str | None
    hops: int
    last_hop: str | None
    attachments: list[str] = field(default_factory=list)
    preview: str = ""


def summarise(raw: bytes) -> Summary:
    """Parse a raw RFC 822 message and keep what the support inbox needs.

    Raises :class:`UnreadableMessage` when the parser rejects the message or
    when it has no sender to reply to.
    """
    try:
        mail = mailparser.parse_from_bytes(raw)
    except MailParserError as error:
        raise UnreadableMessage(f"could not parse the message: {error}") from error

    senders = mail.from_ or []
    if not senders or not senders[0][1]:
        raise UnreadableMessage("the message has no From address")
    sender_name, sender = senders[0]

    # The parser lists the hops oldest first, so the last one is the server that handed us the message.
    hops = mail.received or []
    last_hop = hops[-1].get("by") if hops else None
    attachments = [item.get("filename") or "unnamed" for item in mail.attachments or []]
    sent_at = mail.date.isoformat() if mail.date else None
    body = " ".join((mail.body or "").split())

    return Summary(
        subject=mail.subject or "(no subject)",
        sender=sender,
        sender_name=sender_name or "",
        recipients=[address for _, address in mail.to or [] if address],
        message_id=mail.message_id or "",
        sent_at=sent_at,
        hops=len(hops),
        last_hop=last_hop,
        attachments=attachments,
        preview=body[:PREVIEW_CHARS],
    )
