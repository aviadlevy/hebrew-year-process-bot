# Running the replier

The bot replies to Mastodon mentions from a long-lived container. This
document is the operating contract for that container: what it needs, how to
deploy and roll back, how to read its failure modes, and what it does not
guarantee.

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

A climbing restart count is the signal that the replier is crash-looping.
Exit codes distinguish the failure modes:

- **Exit 2** — missing or invalid configuration. The log names every variable
  that is unset. Check the env file.
- **Exit 1, with a logged exception and a Telegram alert** — a runtime failure
  in the streaming connection (`ChunkedEncodingError`, `ReadTimeout`,
  `ConnectionError`, or anything else mastodon-py raised). The alert carries
  the exception and is sent before the process exits.
- **Exit 1, with only a `mastodon stream closed` warning and no Telegram
  alert** — the server closed the stream cleanly. mastodon-py's
  `handle_stream()` returns normally here rather than raising, so there is no
  exception to alert on. The replier still treats it as failure and exits
  non-zero so the restart is attributable, but the only traces are that log
  line and the restart count. **A climbing restart count with no
  corresponding Telegram alerts is the sign this is happening** — the stream
  is being closed from the far end rather than the process crashing, and it
  is worth investigating even though the container looks "up" in between.

## 8. Known limitations

**There is no healthcheck, deliberately.** The replier has no HTTP surface to
probe, and its real failure mode is not a crashed process — it is a stream
that stays open and looks healthy while silently delivering no mentions. A
liveness probe cannot observe that at all, so adding one would manufacture
confidence rather than reduce risk.

The consequence, stated plainly: **Telegram alerts fire on crashes, not on a
silently-stalled stream.** If the bot goes quiet without crashing, nothing in
this stack will tell you. Periodically checking the logs for a recent mention
being received and answered is currently the only way to notice.

**`read_only: true` is verified only through startup.** Python
initialization, the `python-magic` import, loading certifi's CA bundle, and
constructing the Mastodon client all complete fine on a read-only root
filesystem. The long-lived streaming path — a different code path that runs
for hours or days — has **not** been proven. Watch the first several hours of
logs after a fresh deploy for `Read-only file system` errors. If one appears,
the fix is a narrowly scoped named volume for that specific path, not
removing `read_only`.
