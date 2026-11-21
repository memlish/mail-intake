# mail-intake

Receives the mail that customers send to the support address. The mail
provider posts each message to this service as raw MIME; the service parses
it, keeps a short summary, and the support inbox reads the summaries from here.

Summaries are kept in memory, newest first, up to `MAIL_INTAKE_KEEP`. A restart
clears them: the provider keeps the originals.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `GET` | `/health` | Liveness, the inbox address, and how many summaries are stored |
| `POST` | `/inbound` | One raw message as the request body (`Content-Type: message/rfc822`). Returns its summary with `201` |
| `GET` | `/messages` | Stored summaries, newest first. `?sender=` narrows it to one address |
| `GET` | `/messages/{id}` | One summary |

A summary holds the subject, the sender, the recipients, the message id, when
it was sent, the number of `Received` hops and the last one, the names of any
attachments, and the first 200 characters of the body.

`POST /inbound` answers `415` for anything that is not raw mail, `413` for a
message over the size limit, and `422` for a message that cannot be read or
has no `From` address.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `MAIL_INTAKE_SERVICE_NAME` | `mail-intake` | Name reported on `/health` |
| `MAIL_INTAKE_MAX_BYTES` | `2000000` | Largest raw message accepted |
| `MAIL_INTAKE_KEEP` | `1000` | Summaries kept in memory |
| `MAIL_INTAKE_INBOX_ADDRESS` | `support@example.test` | The address this deployment collects for |

## Running

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/uvicorn mail_intake.app:app --reload
```

## Tests

```sh
.venv/bin/python -m pytest tests/ -q
```
