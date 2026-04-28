# Deploy

## Aktueller Stand

Live-Server: `https://prod-is-lava.dev`

- **Provider:** AWS EC2, eu-central-1, Instance `i-0dcff98f735883d60`, Type `t4g.nano`, Public IP `3.78.184.97`
- **OS:** Ubuntu 24.04 (ARM64)
- **Reverse Proxy:** Caddy mit Auto-HTTPS (LetsEncrypt) auf Domain `prod-is-lava.dev` (+ `mcm.3-78-184-97.sslip.io` als sslip-Fallback)
- **App:** uvicorn auf `127.0.0.1:8000`, läuft als systemd-Unit `mcm-server.service`
- **Code-Pfad auf Server:** `/opt/mcm`
- **Logs:** `journalctl -u mcm-server.service`

## Auto-Deploy (Push auf main)

Bei jedem Push auf `main` läuft die GitHub-Actions-Pipeline `.github/workflows/ci.yml`:

1. **test** — pytest grün
2. **lint-python** — ruff check + format
3. **lint-frontend** — prettier check
4. **deploy** — wenn alle drei grün UND es ein Push auf main ist: Deploy auf EC2

Der Deploy-Job nutzt `scripts/deploy.sh`. Voraussetzung: zwei GitHub-Secrets gesetzt:

| Secret        | Wert                                                                                                    |
| ------------- | ------------------------------------------------------------------------------------------------------- |
| `EC2_SSH_KEY` | Privater SSH-Key (Inhalt der `mcm-game-server.pem` Datei, mit `-----BEGIN ... PRIVATE KEY-----` Zeilen) |
| `EC2_HOST`    | `3.78.184.97` (oder die DNS-Adresse)                                                                    |

Optional:

| Secret     | Default  | Wert               |
| ---------- | -------- | ------------------ |
| `EC2_USER` | `ubuntu` | falls anderer User |

So setzt du die Secrets:

```bash
gh secret set EC2_SSH_KEY < ~/.ssh/mcm-game-server.pem
gh secret set EC2_HOST --body "3.78.184.97"
```

Sind die Secrets nicht gesetzt, läuft der Deploy-Job mit einer Warnung weiter, ohne tatsächlich zu deployen — CI fail't nicht, der Code landet auf main.

## Manueller Deploy

Wenn du lokal pushen willst (z. B. zum schnellen Testen, ohne Push auf main):

```bash
./scripts/deploy.sh
```

Voraussetzungen lokal:

- `~/.ssh/mcm-game-server.pem` (Private-Key für SSH-Zugriff)
- Du musst aus dem Repo-Root aufrufen (Tarball wird aus dem Working-Tree gebaut)

Optional:

```bash
EC2_HOST=3.78.184.97 EC2_USER=ubuntu SSH_KEY=~/.ssh/mcm-game-server.pem ./scripts/deploy.sh
```

## Server starten / stoppen (Kosten sparen)

EC2 läuft 24/7 → ~$3/Monat Compute + ~$3.60/Monat Public-IPv4 + EBS = ~$7/Monat.

Wenn du nicht aktiv testest, Instance stoppen:

```bash
aws ec2 stop-instances --region eu-central-1 --instance-ids i-0dcff98f735883d60
```

Wieder starten:

```bash
aws ec2 start-instances --region eu-central-1 --instance-ids i-0dcff98f735883d60
```

**Achtung:** ohne Elastic IP wechselt die Public IP beim Start. Aktuell hängt das Setup an `3.78.184.97` (sslip.io URL braucht IP-Update; Route53-A-Record für prod-is-lava.dev braucht Update). Bei IP-Wechsel:

- `EC2_HOST` Secret aktualisieren
- `EC2_HOST` in diesem Doc aktualisieren
- Caddyfile auf der Instanz aktualisieren (`/etc/caddy/Caddyfile`), `sudo systemctl reload caddy`
- README + `docs/ROADMAP.md` Live-URL anpassen

Langfristig: Elastic IP zuweisen (~$3.60/Mo, auch beim Stoppen) oder eigene Domain via Route53 / DNS-Provider.

## Server-Innenleben (auf der Instanz)

```bash
# Status
systemctl status mcm-server.service caddy.service

# Logs
journalctl -u mcm-server.service -f
journalctl -u caddy.service -f

# Code-Pfad
cd /opt/mcm

# Manueller Restart der App
sudo systemctl restart mcm-server.service
```

## LLM-Secrets (Tier 3.9)

Die Bot-Manager und der `ai_flavor`-Layer können einen LLM-Provider nutzen
(`AnthropicClient` oder lokales OpenAI-kompatibel). Die API-Keys liegen NICHT
im Repo, sondern als systemd-EnvironmentFile auf der Instance:

```
/etc/mcm-server.env       # root-owned, 0600
```

Inhalt z. B.:

```
ANTHROPIC_API_KEY=sk-ant-...
# oder alternativ:
LLM_LOCAL_BASE_URL=http://localhost:11434/v1
LLM_LOCAL_MODEL=gemma3:4b
```

Im systemd-Unit (`/etc/systemd/system/mcm-server.service`) referenziert via:

```
EnvironmentFile=/etc/mcm-server.env
```

Rotation: Datei editieren + `sudo systemctl restart mcm-server`. Wenn keine
Provider-Variable gesetzt ist, fallen Bots auf reine Heuristik zurück und
`ai_flavor.generate_postmortem` nutzt Templates statt LLM. Spielfähig in
beiden Fällen.

**Recovery-Tip:** Wenn der LLM-Provider Probleme hat (Timeout-Storm, Rate-
Limit), API-Key in `/etc/mcm-server.env` auskommentieren + Service-Restart.
Bots sind sofort wieder responsive (heuristic-only mode). Siehe Tier 3.9.2.1
in der Roadmap für den Live-Incident vom 2026-04-28.

## Caddyfile

Aktuell:

```caddy
mcm.3-78-184-97.sslip.io, prod-is-lava.dev {
    reverse_proxy 127.0.0.1:8000
    encode zstd gzip
}
```

Liegt unter `/etc/caddy/Caddyfile` auf der Instanz. Bei Änderung: `sudo systemctl reload caddy`.

## Notfall-Rollback

Wenn ein Deploy einen Bug einführt, schnellster Rollback:

```bash
# 1. Auf der EC2-Instance: alten Tag auschecken (da kein Git-Clone, geht das so nicht direkt)
# Stattdessen: lokal den vorherigen Tag auschecken und manuell deployen
git checkout <vorheriger-tag-oder-sha>
./scripts/deploy.sh
git checkout main
```

Für die Zukunft: Deploy-Script könnte den vorherigen Tarball auf der Instanz aufbewahren, sodass `--rollback` möglich wäre. (Tier 0 Polish, nicht jetzt.)

## Initial-Setup (Historisch — nicht mehr nötig)

Die Instance wurde am 2026-04-25 aufgesetzt mit:

- Ubuntu 24.04 ARM64 AMI
- Security Group `mcm-game-sg` (22, 80, 443)
- Userdata installiert Caddy + uv
- Tarball + scp + systemd-Unit-Setup

Wenn die Instance jemals neu aufgesetzt werden muss, sind die Schritte im Repo-Verlauf dokumentiert (commits ~`f68e210` und früher).
