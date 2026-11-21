"""The intake API, through FastAPI's test client."""
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from mail_intake import app as intake

RAW = (
    b"Received: from mail.sender.example ([198.51.100.7]) by mx.support.example; Tue, 3 Nov 2026 09:15:02 +0000\r\n"
    b"Received: from laptop.sender.example ([203.0.113.9]) by mail.sender.example; Tue, 3 Nov 2026 09:15:00 +0000\r\n"
    b"Message-ID: <order-1182@sender.example>\r\n"
    b"Subject: Order 1182 arrived damaged\r\n"
    b"From: Dana Reyes <dana@customer.example.test>\r\n"
    b"To: support@example.test\r\n"
    b"Date: Tue, 3 Nov 2026 09:15:00 +0000\r\n"
    b"\r\n"
    b"The box was open when it arrived.\r\n"
)
RFC822 = {"Content-Type": "message/rfc822"}


@pytest.fixture
def client():
    intake.inbox = intake.Inbox(intake.settings.keep)
    return TestClient(intake.app)


def test_health_names_the_inbox(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["inbox"] == "support@example.test" and body["stored"] == 0


def test_a_message_is_summarised_and_stored(client):
    response = client.post("/inbound", content=RAW, headers=RFC822)
    assert response.status_code == 201
    message = response.json()
    assert message["subject"] == "Order 1182 arrived damaged"
    assert message["sender"] == "dana@customer.example.test" and message["sender_name"] == "Dana Reyes"
    assert message["recipients"] == ["support@example.test"]
    assert message["preview"] == "The box was open when it arrived."
    assert client.get(f"/messages/{message['id']}").json() == message


def test_received_hops_are_counted(client):
    message = client.post("/inbound", content=RAW, headers=RFC822).json()
    assert message["hops"] == 2 and message["last_hop"] == "mx.support.example"


def test_attachments_are_listed_by_name(client):
    mail = EmailMessage()
    mail["From"] = "dana@customer.example.test"
    mail["To"] = "support@example.test"
    mail["Subject"] = "Photo of the box"
    mail.set_content("Photo attached.")
    mail.add_attachment(b"not really a picture", maintype="image", subtype="png", filename="box.png")
    message = client.post("/inbound", content=mail.as_bytes(), headers=RFC822).json()
    assert message["attachments"] == ["box.png"]


def test_a_message_with_no_sender_is_refused(client):
    response = client.post("/inbound", content=b"Subject: hello\r\n\r\nno sender here\r\n", headers=RFC822)
    assert response.status_code == 422 and "From" in response.json()["detail"]


def test_only_raw_mail_is_accepted(client):
    assert client.post("/inbound", json={"subject": "hi"}).status_code == 415
    assert client.post("/inbound", content=b"", headers=RFC822).status_code == 400


def test_an_oversized_message_is_refused(client, monkeypatch):
    monkeypatch.setattr(intake.settings, "max_bytes", 64)
    assert client.post("/inbound", content=RAW, headers=RFC822).status_code == 413


def test_messages_are_listed_newest_first_and_by_sender(client):
    client.post("/inbound", content=RAW, headers=RFC822)
    client.post("/inbound", content=RAW.replace(b"dana@customer", b"sam@other"), headers=RFC822)
    listed = client.get("/messages").json()
    assert listed["count"] == 2 and listed["messages"][0]["sender"] == "sam@other.example.test"
    assert client.get("/messages", params={"sender": "dana@customer.example.test"}).json()["count"] == 1
    assert client.get("/messages/999").status_code == 404
