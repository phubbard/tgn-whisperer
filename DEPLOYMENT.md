# Deployment Guide

This guide covers deploying the Prefect-based podcast processing system to run automatically.

## 1. Install Prefect Server as a Systemd Service

The Prefect server needs to run at boot time so the web interface is available.

### Install the service:

```bash
# Copy the service file to systemd directory
sudo cp prefect-server.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start at boot
sudo systemctl enable prefect-server

# Start the service now
sudo systemctl start prefect-server

# Check the service status
sudo systemctl status prefect-server
```

### View logs:
```bash
# Follow service logs
sudo journalctl -u prefect-server -f

# View recent logs
sudo journalctl -u prefect-server -n 100
```

### Service management:
```bash
# Stop the service
sudo systemctl stop prefect-server

# Restart the service
sudo systemctl restart prefect-server

# Disable auto-start at boot
sudo systemctl disable prefect-server
```

## 2. Update Crontab to Run Prefect Workflow

Replace the old `make`-based cron job with the new Prefect-based workflow.

### Update crontab:

```bash
crontab -e
```

**Replace this line:**
```
2 7 * * * bin/tgn
```

**With this:**
```
2 7 * * * bin/tgn-prefect
```

The new script runs all three podcasts (TGN, WCL, Hodinkee) via Prefect at 7:02 AM daily.

### Test the script manually:

```bash
# Run all podcasts
~/bin/tgn-prefect

# Or run individually
cd ~/code/tgn-whisperer
uv run python app/run_hodinkee.py
```

## 3. Access the Prefect Web Interface

Once the service is running, access the web interface:

- **Network:** https://prefect.phfactor.net
- **Local:** http://localhost:4200

## 4. Monitor Workflow Runs

### View workflow history:
Go to the Prefect UI → Flows → Flow Runs

### Check logs:
Click on any flow run to see detailed logs for each task

### View current runs:
The UI shows real-time updates as workflows execute

## Notes

- The Prefect server stores data in `~/.prefect/`
- Workflow runs are persisted in the Prefect database
- Log level is set to DEBUG for detailed output
- Cloud upgrade prompts are disabled in the UI
