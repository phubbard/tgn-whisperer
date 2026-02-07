# Prefect Webhook Fix - 2026-02-05

## Problem
Prefect automations were failing to call webhooks with error:
```
Action failed: "Webhook call failed: ReadError('')"
```

## Root Cause
- Prefect server's HTTP client in the automation engine lacked proper timeout configuration
- Connection pool issues after extended uptime
- The webhooks themselves were working (ntfy.sh and Slack), but the server couldn't read responses

## Solution Applied

### 1. Updated Prefect Server Configuration
Added HTTP timeout environment variables to `/etc/systemd/system/prefect-server.service`:

```ini
Environment="PREFECT_API_REQUEST_TIMEOUT=30.0"
Environment="HTTPX_TIMEOUT=30.0"
```

### 2. Restarted Prefect Server
```bash
sudo systemctl daemon-reload
sudo systemctl restart prefect-server
```

## Webhook Configurations

### Active Automations
1. **"Push notification on run failure"** (ID: 87d08538-20ea-4551-933d-09d931571eab)
   - Webhook: ntfy.sh
   - URL: https://ntfy.sh/tgn-whisperer-errors
   - Triggers: On flow run Crashed or Failed
   - Sends: Flow name, run ID, state, message, UI link

2. **"ping slack on run"** (ID: 0a1500b7-a9fe-4ae0-b2f2-c10acee08edc)
   - Webhook: Slack
   - URL: hooks.slack.com/services/TNRH9NY1Z/B0ACR596BUY/...
   - Triggers: On any flow run event
   - Sends: Flow name, run name, state

3. **"ping slack when done"** (ID: 0fb5824e-409c-45c6-a36b-b896f9e6de6e)
   - Webhook: Slack
   - URL: Same as above
   - Triggers: On Completed, Failed, Crashed, or TimedOut
   - Sends: Flow name, run name, final state

## Testing
Webhooks tested successfully after configuration:
```bash
✓ ntfy webhook working: HTTP 200
✓ Slack webhook working: HTTP 200
```

## Monitoring
Check for webhook errors:
```bash
sudo journalctl -u prefect-server --since "1 hour ago" | grep "Webhook call failed"
```

## If Errors Return
1. Restart Prefect server: `sudo systemctl restart prefect-server`
2. Check webhook URLs are accessible: Test with curl
3. Consider disabling high-frequency automation "ping slack on run" if it overwhelms connection pool
4. Update Prefect to newer version if bug persists

## Service File Backup
Original service file backed up to:
`/etc/systemd/system/prefect-server.service.backup`
