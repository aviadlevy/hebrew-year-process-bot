# Running the bot

This document covers two workloads on one host: the long-lived Mastodon
mention replier, and the daily progress post that runs as a systemd timer.
It is the operating contract for both: what each needs, how to deploy and
roll back, how to read their failure modes, and what they do not guarantee.

It assumes a Linux host you can reach over SSH, with an account that can
`sudo`. Nothing here is specific to a particular machine.

## 1. Host prerequisites

Install Docker CE from Docker's official apt repository — not the snap, and
not the convenience script — including the Compose plugin:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

sudo systemctl enable --now docker
```

Every `docker` command here runs under `sudo`, and your login account is
deliberately **not** added to the `docker` group. Membership in that group is
root-equivalent — the daemon socket will bind any host path into a container as
root — so adding your user would silently undo the file permissions in §2.

`systemctl enable` matters: it is what brings the container back after a host
reboot, together with the compose file's `restart: unless-stopped`.

## 2. Configuration

The container reads its configuration from an env file created by hand on the
host and never committed. `deploy/env.example` is the template; the real file
lives only on the host, conventionally at `/opt/hypb/.env`.

Four secrets plus the image tag:

| Variable | Where it comes from |
|---|---|
| `MASTODON_ACCESS_TOKEN` | On your Mastodon instance: Preferences → Development → Applications. Create or reuse an application with read/write scope for the bot account and copy its access token. |
| `MASTODON_BASE_URL` | The base URL of that instance, e.g. `https://mastodon.social`. |
| `TELEGRAM_TOKEN` | Message [@BotFather](https://t.me/BotFather), create a bot, copy the token. |
| `TELEGRAM_CHAT_ID` | Send the bot any message, then call `https://api.telegram.org/bot<TELEGRAM_TOKEN>/getUpdates` and read `message.chat.id`. |
| `IMAGE_TAG` | Which published image to run — see [§3](#3-pick-an-image-tag). Not a secret, but required. |

One optional setting: `LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
Unset means `INFO`, which logs every mention received and every reply sent.
`DEBUG` adds each raw stream event and the ~15s keepalives — useful when the
stream looks stuck and you need proof the connection is alive. An unrecognised
value falls back to `INFO` with a warning rather than stopping the replier.

The env file must be owned `root:root`, mode `0600`. `0600` is the part that
matters: the tokens stay unreadable to every other account on the host, and to
anything running as your login user — a backup job, a stray `scp -r`. Root
ownership is what keeps that true, given that no unprivileged account is in the
`docker` group (§1). Set the ownership **after** filling in the values;
afterwards every edit needs `sudo`.

All four secrets are **hard requirements**. The process validates them at
startup and exits 2 naming every one that is missing, rather than failing
later in a way that is hard to trace. In particular, a missing
`TELEGRAM_TOKEN` would otherwise make every failure alert 404 silently —
the alerting path would break exactly when it was needed.

## 3. Pick an image tag

Images are published to
`ghcr.io/aviadlevy/hebrew-year-process-bot`. The package is **public**, so the
host needs no registry login and no credentials to pull — do not go hunting
for a token that is not required.

**If your host is ARM (`aarch64`), this is the most common way a first deploy
fails.** Multi-arch publishing was added in the same change as this document.
Every tag up to and including `v3.1.2` was built **amd64-only** and will not
run on an ARM host. `:latest` continues to point at the last amd64-only
release until a newer release tag is cut.

Before deploying a tag, confirm it lists both `linux/amd64` and `linux/arm64`:

```bash
docker buildx imagetools inspect \
    ghcr.io/aviadlevy/hebrew-year-process-bot:<tag>
```

Deployments pin an explicit release tag. Do not run `:main` or `:latest` — a
pinned tag is what makes "what is running" unambiguous and rollback a
one-line change.

### Cutting a release tag

`.github/workflows/docker.yaml` publishes on pushes to `main` and on `v*`
tags. Pull requests build both architectures to validate the Dockerfile but
publish nothing. So after multi-arch support merges to `main`, the only new
multi-arch tag is `:main` — which deployments must not use. Cut a release
tag to get a deployable one:

```bash
git tag v3.2.0
git push origin v3.2.0
```

Wait for the workflow triggered by that tag push to finish. That tag is what
goes in `IMAGE_TAG`.

## 4. First deploy

Create the deploy directory on the host and copy in the three files from
this repo's `deploy/` directory:

```bash
# on the host
sudo mkdir -p /opt/hypb
sudo chown "$USER:$USER" /opt/hypb
```

```bash
# from your local checkout
scp deploy/compose.yaml deploy/deploy.sh deploy/env.example \
    <user>@<host>:/opt/hypb/
```

Then, on the host, turn the template into the real secret-bearing file:

```bash
cd /opt/hypb
cp env.example .env
$EDITOR .env          # fill in IMAGE_TAG and the four secrets

sudo chown root:root .env
sudo chmod 600 .env
chmod +x deploy.sh
```

Deploy:

```bash
sudo ./deploy.sh
```

`deploy.sh` pulls the pinned tag, brings the container up, and prints its
status and recent logs. It reads `/opt/hypb` by default (override with
`COMPOSE_DIR`), refuses to run if `.env` is missing, and is otherwise
equivalent to the `docker compose` commands below — a convenience wrapper,
not a dependency.

**Confirm the deploy on Telegram.** Every start sends a notice naming the
deploy it came from:

```
hypb mastodon replier started
version: v4.0.0
instance: https://mastodon.social
host: 8f3c1d9e4b7a
started: 2026-08-18 20:48:11 IDT
```

If that message does not arrive, alerting is broken and every later section of
this document that says "you will be paged" is false. The log says which half
failed: `telegram rejected the alert: HTTP 400 ...` means the credentials
reached Telegram and were refused — a wrong `TELEGRAM_CHAT_ID` reads
`chat not found`, a wrong `TELEGRAM_TOKEN` reads `Unauthorized` — while
`telegram alert could not be sent` means the request never got there. The bot
token is redacted from both. A failed notice is logged, not fatal: answering
mentions matters more than being able to page anyone.

## 5. Routine deploy

```bash
cd /opt/hypb
sudo $EDITOR .env         # update IMAGE_TAG to the new release
sudo docker compose pull
sudo docker compose up -d
```

The ARM caveat in §3 applies to every deploy, not only the first.

## 6. Rollback

Every deploy is one pinned tag, so rolling back is the same change in
reverse:

```bash
cd /opt/hypb
sudo $EDITOR .env         # set IMAGE_TAG back to the previous good release
sudo docker compose pull
sudo docker compose up -d
```

There is no separate rollback mechanism to learn.

## 7. Observing

```bash
cd /opt/hypb
sudo docker compose logs -f     # tail logs
sudo docker compose ps          # status and restart count
```

The startup notice described in §4 arrives on every start, not only the first,
so an unexpected one in Telegram means the container restarted.

A climbing restart count is the signal that the replier is crash-looping.
It is a trustworthy signal: a dropped stream no longer restarts the container.

**Dropped connections are expected and are handled in-process.**
mastodon.social recycles long-lived SSE connections — in practice a few times
a day — and the blocking `stream_user()` cannot recover from that on its own,
because mastodon-py's reconnect loop only exists on its `run_async=True` path.
`hypb/stream_supervisor.py` reconnects instead, so a recycle costs a second of
downtime rather than a container restart, and it does not page anyone. In the
log it looks like this, at WARNING, and nothing else happens:

```
mastodon stream ended (MastodonNetworkError('Server ceased communication.')); reconnecting in 1s
```

Reconnects back off 1s → 2s → 4s … capped at 60s. A stream that stayed up for
5s had connected, so its drop resets the backoff: a server that cuts every
stream after ~15s costs a second of downtime per cut, not a growing delay. A
stream that stayed up for 60s counts as healthy and also ends the outage, so
the five-minute alert below only fires if streams keep failing to stay up.

Exit codes and alerts distinguish what is left:

- **Exit 2** — missing or invalid configuration. The log names every variable
  that is unset. Check the env file.
- **Exit 1, with a logged exception and a Telegram alert** — a failure the
  supervisor deliberately will not retry: anything that is not a transport
  error. A `MastodonMalformedEventError` (a parsing bug, as in the keepalive
  bug), a rejected token, or a plain bug all land here. These *should* page,
  and they crash-loop until fixed.
- **A Telegram alert reading `mastodon stream down for Nm, still retrying`,
  with no restart** — reconnects have been failing continuously for five
  minutes. The process is alive and still trying; this is the far end or the
  network being down, not the bot. Exactly one alert is sent per outage, and
  recovery is logged at INFO (`mastodon stream recovered after Ns of failed
  reconnects`) rather than alerted.

## 8. Known limitations

**There is no healthcheck, deliberately.** The replier has no HTTP surface to
probe, and its real failure mode is not a crashed process — it is a stream
that stays open and looks healthy while silently delivering no mentions. A
liveness probe cannot observe that at all, so adding one would manufacture
confidence rather than reduce risk.

The consequence, stated plainly: **Telegram alerts fire on crashes and on
sustained reconnect failures, not on a silently-stalled stream.** If the bot
goes quiet while its connection still looks open, nothing in this stack will
tell you. Periodically checking the logs for a recent mention being received
and answered is currently the only way to notice.

**Mentions that arrive mid-reconnect are lost.** The streaming API has no
replay and nothing backfills notifications after a reconnect, so anything
posted during the gap is never seen. Reconnecting in-process shrinks that gap
from a container restart to roughly a second for the common case, but does not
close it.

**`read_only: true` is verified only through startup.** Python
initialization, the `python-magic` import, loading certifi's CA bundle, and
constructing the Mastodon client all complete fine on a read-only root
filesystem. The long-lived streaming path — a different code path that runs
for hours or days — has **not** been proven. Watch the first several hours of
logs after a fresh deploy for `Read-only file system` errors. If one appears,
the fix is a narrowly scoped named volume for that specific path, not
removing `read_only`.

## 9. The daily progress post

The progress post is a **one-shot**, not a service: a systemd timer runs the
same pinned image with its entrypoint overridden to `hypb-progress`. It shares
the replier's image, its `IMAGE_TAG`, and its four secrets, and adds five of
its own.

### 9.1 Why it remembers things in a database

It used to recover the last published percentage by fetching its own last 50
Mastodon statuses and regexing the number out of the rendered HTML. That
coupled posting to Mastodon's markup, and crashed the run with a raw
`TypeError` whenever those 50 statuses held no progress bar.

It now keeps the number in SQLite on a named volume, **keyed by platform**.
That last part matters operationally: if Twitter fails and Mastodon succeeds,
each keeps its own position, so the failed one retries on the next run while
the successful one does not repeat itself. A run reports `posted`, `skipped`,
`seeded` or `failed` per platform, and exits 1 if any platform failed.

If a platform has no row yet, the run falls back to reading the Mastodon
timeline once — so a lost volume recovers on its own. If that finds nothing
either, it records the current percentage **without posting**: one skipped day
at worst, never a double post.

### 9.2 Extra configuration

Five variables beyond §2, in a **second** file, `/opt/hypb/progress.env`, also
`root:root` and `0600`:

| Variable | Where it comes from |
|---|---|
| `MASTODON_USER_ID` | The bot's numeric account id on its instance. |
| `CONSUMER_KEY`, `CONSUMER_SECRET` | Twitter app credentials — Keys and tokens. |
| `ACCESS_KEY`, `ACCESS_SECRET` | Twitter access token and secret for the bot account. |

They live apart from `.env` on purpose: the replier is long-lived and has no
use for Twitter credentials, so they stay out of its environment. Neither file
repeats a secret the other holds, so the two cannot drift.

`BEARER_TOKEN`, which the GitHub Actions workflow exports, is **not** required
— it belongs to the Twitter streaming client, which this path never touches.

### 9.3 Install

**Pin an `IMAGE_TAG` that contains the state store first.** The state store
landed in this branch; any tag cut before it still runs the old
`get_last_state()`-only `tweet()`, which awaits Twitter before Mastodon and
crashes with a raw `TypeError` the moment the last 50 statuses hold no
progress toot. If `IMAGE_TAG` in `/opt/hypb/.env` still points at such a tag,
`sudo systemctl start hypb-progress.service` below starts the old code against
the live account, and the traceback it produces reads like this document's fix
is broken rather than like a stale pin. Cut a release tag from a checkout that
includes the state store (§3), then update `IMAGE_TAG` the same way as any
other deploy (§5), before continuing.

```bash
# from your local checkout
scp deploy/progress-run.sh deploy/progress.env.example \
    <user>@<host>:/opt/hypb/
scp deploy/hypb-progress.service deploy/hypb-progress.timer \
    <user>@<host>:/tmp/
```

```bash
# on the host
cd /opt/hypb
cp progress.env.example progress.env
$EDITOR progress.env          # fill in the five values
sudo chown root:root progress.env
sudo chmod 600 progress.env
chmod +x progress-run.sh

sudo install -m 0644 /tmp/hypb-progress.service /tmp/hypb-progress.timer \
    /etc/systemd/system/
sudo systemctl daemon-reload
```

**Hand `progress-run.sh` and its directory to root.** The timer runs this
script unattended, as root, once a day — `ExecStart` in
`hypb-progress.service` has no other way to invoke it. `chmod +x` above only
sets the execute bit; the script and `/opt/hypb` itself are still owned by
your login user from §4, which means anything running as that user can
rewrite the script, or — since directory write permission allows unlinking —
delete and replace the `0600 root:root` `.env` with one pointing `IMAGE_TAG` at
an arbitrary image that then runs as root on a timer. That is exactly the
escalation §1 keeps your user out of the `docker` group to prevent, so the
script and its directory need the same root ownership:

```bash
sudo chown root:root /opt/hypb/progress-run.sh
sudo chmod 755 /opt/hypb/progress-run.sh
sudo chown root:root /opt/hypb
```

§2 already warns that every later edit under `/opt/hypb` needs `sudo` once
ownership moves to root, so this changes nothing about the routine deploys in
§5 and §6.

**Create the state volume, and give it to the container's user.** A fresh named
volume is created `root:root`, and the image runs as uid 10001 — without this
the first run fails on a write it cannot do:

```bash
sudo docker volume create hypb-state
sudo docker run --rm -v hypb-state:/var/lib/hypb --user 0:0 \
    --entrypoint chown \
    ghcr.io/aviadlevy/hebrew-year-process-bot:<IMAGE_TAG> \
    -R 10001:10001 /var/lib/hypb
```

Prove one real run before enabling the timer:

```bash
sudo systemctl start hypb-progress.service
sudo journalctl -u hypb-progress.service -n 50 --no-pager
```

**Retire the GitHub Actions schedule before enabling the timer.** Nothing
else does this for you, and the timer's `OnCalendar` fires at the same
instant as the existing cron (§9.4) — leave both live and the percentage gets
posted twice a day, from two different runners, until someone notices.
Comment out the `schedule:` block in `.github/workflows/tweet.yaml`, keep
`workflow_dispatch:`, and commit:

```yaml
on:
  # schedule:
  #   - cron:  '0 7 * * *'
  workflow_dispatch:
```

Keep `workflow_dispatch:` — do not delete the workflow. It is the manual
fallback for posting if the host is down, so it has to stay callable even
while the schedule is off.

Then enable the timer:

```bash
sudo systemctl enable --now hypb-progress.timer
systemctl list-timers hypb-progress.timer
```

### 9.4 Changing the time

The host runs in `Etc/UTC` (`timedatectl`), so the shipped
`OnCalendar=*-*-* 07:00:00` fires at the same instant as the GitHub Actions
cron it replaced. **Do not edit the unit file** — use a drop-in, which survives
reinstalling it:

```bash
sudo systemctl edit hypb-progress.timer
```

```ini
[Timer]
OnCalendar=
OnCalendar=*-*-* 07:00:00 Asia/Jerusalem
```

The empty `OnCalendar=` first is required: without it systemd *adds* a
schedule rather than replacing one, and the job fires twice.

### 9.5 Observing

```bash
sudo journalctl -u hypb-progress.service --since '2 days ago'
systemctl list-timers hypb-progress.timer     # last and next firing
```

Every run also sends a Telegram summary naming each platform's outcome. Most
days it reports `skipped` for both — the percentage only moves about every 3.5
days, since a ~354-day year covers 100 steps.

Read the state directly if you need to. `<IMAGE_TAG>` below is whatever is
currently pinned in `/opt/hypb/.env`, which is `0600 root:root`:

```bash
sudo grep IMAGE_TAG /opt/hypb/.env
```

```bash
sudo docker run --rm -v hypb-state:/var/lib/hypb --user 10001:10001 \
    --entrypoint python \
    ghcr.io/aviadlevy/hebrew-year-process-bot:<IMAGE_TAG> \
    -c "import sqlite3; print(sqlite3.connect('/var/lib/hypb/state.db').execute('SELECT * FROM post_state').fetchall())"
```

### 9.6 Rollback

To go back to GitHub Actions, disable the timer, then re-enable the
`schedule:` block:

```bash
sudo systemctl disable --now hypb-progress.timer
```

then uncomment `cron:` in `.github/workflows/tweet.yaml` (§9.3) and commit.
Running both at once — during the switch, or if you forget to disable one
side — is survivable but pointless: whichever fires first posts and records,
and the second sees the current percentage already stored and posts nothing.
