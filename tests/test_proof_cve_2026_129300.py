"""Regression test: a message with an unusable Received date must still be accepted.

A Received header is written by whoever relays the message, so its date can be
anything. One hop with a year far out of range must not cost us the whole
message: the summary should be stored and the hop simply has no usable date.
This fails while the parser lets that date blow up the parse, and passes once
the parser copes with it.

Self-contained: it puts the package source on sys.path itself.
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient  # noqa: E402

from mail_intake.app import app  # noqa: E402

RAW = (
    b"Received: from x ([1.2.3.4]) by mx.support.example; Tue, 7 Mar 292277026596 14:29:24 +0000\r\n"
    b"Subject: hi\r\n"
    b"From: a@example.test\r\n"
    b"To: support@example.test\r\n"
    b"\r\n"
    b"body\r\n"
)


def test_message_with_out_of_range_received_date_is_still_accepted():
    response = TestClient(app).post("/inbound", content=RAW, headers={"Content-Type": "message/rfc822"})
    assert response.status_code == 201
    assert response.json()["subject"] == "hi"
