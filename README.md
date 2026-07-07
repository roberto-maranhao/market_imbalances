# market_imbalances
This project may make you lose money. Use at your own risk. Never trust its results.

## Disclaimer

This is an educational/experimental project, not financial advice. Nothing here is a
recommendation to buy, sell, or hold any security, commodity, or currency. Data sources
may be delayed, incomplete, or wrong, and the correlation/cointegration signals can fail
or break down without warning. The author(s) are not responsible for any investment
decisions made using this software or for any financial losses that result from its use.
You are solely responsible for your own investment decisions.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in BRAPI_TOKEN / FRED_API_KEY, see .env.example for where to get them
python -m src.collectors.backfill   # one-off: pulls years of history for the monitored pairs
python -m src.signals.run_daily     # computes cointegration/z-score/correlation from that history
python -m src.web.wsgi              # dev server at http://0.0.0.0:8000
```

See `plan.json` for the full design (data sources, theory, roadmap) and
`.claude/agents/market-imbalances-builder.md` for the agent that implements it phase by phase.

## Running on a Raspberry Pi

The app is a plain Flask app served by gunicorn, backed by SQLite — no separate database
server, no build step. `deploy/` has templates for the two pieces that make it run
unattended:

- `deploy/market-imbalances.service` — a systemd unit that runs gunicorn. Copy it to
  `/etc/systemd/system/`, edit the `User`/`Group`/paths for your setup, then:
  ```
  sudo systemctl daemon-reload
  sudo systemctl enable --now market-imbalances
  ```
- `deploy/crontab.example` — daily cron entries that run the data collectors and then the
  signal engine (in that order) once markets have closed. Copy the two lines into
  `crontab -e` for the user running the service, and `mkdir -p var/log` first (cron doesn't
  create the log directory for you).

**Security note:** as configured, the app binds to `0.0.0.0` with no authentication —
anyone who can reach that IP:port on your network can view it. This is intentional for the
initial single-user, local-network scope described in `plan.json`, but do **not** port-forward
it to the public internet as-is. If you need remote access, put it behind a VPN (e.g.
Tailscale/WireGuard) or a reverse proxy with authentication, rather than exposing the port
directly.
