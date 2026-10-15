# ExamSentinel on a campus server

Everything - the web app, the API, PostgreSQL, Redis, the code sandbox, HTTPS and nightly
backups - runs on one Linux server with Docker. During exams nothing needs the internet: the
editor, the face-detection model and all other assets are served by the server itself.

```
lab PCs ──https──► proxy (nginx)  ─┬─ /api ──► backend (API, 4 worker processes)
                                   └─ /    ──► frontend (web app)
                   db (PostgreSQL 16) · redis · engine (code sandbox) · backup (nightly dumps)
```

## Contents

- [Requirements](#requirements)
- [HTTPS certificate](#https-certificate)
- [Install](#install)
- [Day-to-day operation](#day-to-day-operation)
- [Backups and restore](#backups-and-restore)
- [Updating](#updating)
- [Settings](#settings)
- [Troubleshooting](#troubleshooting)

## Requirements

| | |
|---|---|
| OS | Ubuntu Server 22.04 / 24.04 (any Linux with Docker; the code sandbox needs a Linux kernel) |
| Software | Docker Engine with the Compose plugin, `git`, `openssl` |
| Size, up to ~500 students at once | 8 CPU cores, 16 GB RAM, 100 GB SSD (12-16 cores if `WITH_AI=true`) |
| Network | a fixed address on the campus network, ports **80 and 443** open from the labs |
| Name | a DNS name for that address, e.g. `exam.college.edu` |
| Internet | only during installation and updates (images, packages, code runtimes) |

The code sandbox container runs **privileged** so it can isolate each student program. It holds
no secrets and has no published port; keep this server dedicated to ExamSentinel.

## HTTPS certificate

HTTPS is required: browsers allow the webcam and microphone only on HTTPS pages. Put the
certificate in `deploy/campus/certs/` as `fullchain.pem` (certificate + chain) and `privkey.pem`.

- **College certificate authority** (often the easiest on a campus network): issue a certificate
  for `exam.college.edu`. The CA must already be trusted by lab PCs.
- **Let's Encrypt** (free; the name must exist in public DNS):
  - server reachable from the internet on port 80: after `setup.sh`, run
    `sudo certbot certonly --webroot -w deploy/campus/acme -d exam.college.edu`, copy the two files
    from `/etc/letsencrypt/live/exam.college.edu/` into `certs/`, then `docker compose restart proxy`;
  - internal-only server: use certbot's DNS challenge for your DNS provider.
- **Purchased certificate**: same two files.

Without a certificate, `setup.sh` creates a temporary self-signed one. Browsers then show a
warning, so replace it before students use the system.

## Install

```bash
git clone https://github.com/vishwa-10147/ExamSentiinel.git examsentinel
cd examsentinel/deploy/campus
# optional: copy fullchain.pem and privkey.pem into certs/ first
sh setup.sh exam.college.edu admin@college.edu
```

`setup.sh` writes `.env` with random secrets (and prints the first admin's password), builds the
images, creates the database, applies migrations, creates the first admin, starts everything,
installs the code-sandbox runtimes (about 1 GB, once) and loads the practice problem bank. It is
safe to run again.

Then open `https://exam.college.edu`, sign in as the admin, change the password, and create
staff and student accounts under **Admin → User Management** (or import them as CSV).

## Day-to-day operation

Run these in `deploy/campus/`:

| Task | Command |
|---|---|
| Status | `docker compose ps` |
| Health (database, Redis, sandbox, judging backlog) | `docker compose exec backend curl -s localhost:8000/api/health` |
| Logs | `docker compose logs -f backend` (or `frontend`, `proxy`, `engine`, `backup`) |
| Restart everything | `docker compose restart` |
| Stop / start | `docker compose down` / `docker compose up -d` (data is kept) |

Containers restart by themselves after a crash or a reboot. Webcam evidence is stored in
`data/evidence/` and shown to staff through signed links that expire after 15 minutes.

## Backups and restore

- Every night at `BACKUP_HOUR` (default 02:00) the database is dumped into `backups/`; dumps
  older than `BACKUP_KEEP_DAYS` (default 14) are deleted.
- A backup on the same disk does not survive a disk failure: **copy `backups/` and
  `data/evidence/` to another machine every day** (rsync, the college backup system, ...).
- Back up now: `docker compose exec backup sh /backup.sh now`
- Restore (replaces all current data; asks for confirmation and saves the current data first):
  `sh restore.sh backups/examsentinel-YYYYMMDD-HHMMSS.dump`

Test a restore once before relying on the backups (for example on a spare machine).

## Updating

Outside exam hours, from the repository:

```bash
git pull
sh deploy/campus/update.sh
```

It takes a backup, rebuilds, applies database migrations, restarts (about a minute of downtime)
and reloads the practice problem bank. If a migration cannot apply, it stops before restarting.

## Settings

`.env` (written by `setup.sh`; keep it private) holds everything. See `.env.example` for:

- `WEB_CONCURRENCY` - API worker processes (default 4; about one per 2 CPU cores)
- e-mail for password-reset codes - a campus SMTP relay works without internet
- `WITH_AI=true` - server-side phone/person detection and interview transcription (bigger
  image, more CPU); rebuild with `sh update.sh`
- single sign-on with the college's Microsoft/Google/OIDC accounts (needs internet)
- `NEXT_PUBLIC_ICE_SERVERS` - a TURN server if live interviews must cross restrictive networks

## Troubleshooting

| Symptom | Check |
|---|---|
| Browser warns about the certificate | `certs/` still holds the temporary self-signed certificate, or the name typed differs from `SERVER_NAME` |
| Webcam blocked | the page must be opened over `https://` with a trusted certificate |
| "Code execution engine is unavailable" | `docker compose logs engine`; re-run the runtime install step in `setup.sh` |
| Health shows `degraded` | which component is unhealthy: `docker compose exec backend curl -s localhost:8000/api/health` |
| Students get "Too many requests" when a whole lab signs in | raise `LOGIN_RATE_LIMIT_PER_IP` in `.env` (default 300 sign-ins per minute per address; matters when a lab is behind one NAT address), then `docker compose up -d` |

---

Verified end to end on a local rehearsal of this exact setup; see
[Production readiness](../../docs/PRODUCTION_READINESS.md#campus-server).
