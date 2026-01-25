# Viewing Logs and Debugging Crashes in Prefect

## Overview

All TGN Whisperer tasks and flows now use Prefect's `get_run_logger()` for logging, ensuring all log messages appear in the Prefect UI with proper task/flow context.

## Accessing the Prefect UI

```bash
# Web UI
http://localhost:4200
# or on the network
http://webserver.phfactor.net:4200
```

## Viewing Flow Run Logs

### 1. From the Dashboard

1. Go to http://webserver.phfactor.net:4200
2. Click **Runs** in the left sidebar
3. Find your flow run (e.g., "tgn-deploy", "wcl-deploy")
4. Click on the run to see details

### 2. From Flow Run Details

Once you're viewing a specific flow run:

- **Overview Tab**: Shows run status, duration, and high-level info
- **Logs Tab**: Shows ALL logs from the entire flow (including all nested tasks)
- **Tasks Tab**: Shows individual task runs and their status
- **Results Tab**: Shows return values from tasks

## Viewing Task-Specific Logs

To see logs from a specific task:

1. Go to the **Tasks** tab in a flow run
2. Click on the specific task (e.g., "build-site", "attribute-speakers")
3. Click the **Logs** tab to see only that task's logs

## Understanding Log Levels

All logs now include proper context:

```
09:20:16.646 | INFO    | Task run 'build-site-bd6' - Building site for tgn with zensical
09:20:16.647 | DEBUG   | Task run 'build-site-bd6' - Site directory: /home/pfh/code/tgn-whisperer/sites/tgn
```

Format: `TIMESTAMP | LEVEL | Task/Flow context - Message`

## When a Task Crashes

Tasks now log extensive error details before raising exceptions:

### Subprocess Failures (wget, zensical, pagefind, rsync)

```
ERROR | Task run 'build-site-xxx' - zensical build failed with return code 1
ERROR | Task run 'build-site-xxx' - Command: /path/to/zensical build --clean
ERROR | Task run 'build-site-xxx' - STDOUT:
<complete zensical output>
ERROR | Task run 'build-site-xxx' - STDERR:
<any error messages>
```

###API Failures (Claude, Fluid Audio)

```
ERROR | Task run 'attribute-speakers-xxx' - Claude API call failed: <error>
ERROR | Task run 'attribute-speakers-xxx' - Message content: <response text>
```

### General Python Exceptions

Prefect automatically captures Python tracebacks and shows them in the logs.

## Normal Build Output

We now log successful subprocess output too:

```
INFO  | Task run 'build-site-xxx' - Zensical output:
<zensical build progress>
INFO  | Task run 'generate-search-index-xxx' - Pagefind output:
<pagefind indexing stats>
```

## Common Issues and Where to Look

### Episode Processing Failures
- **Task**: `process-episode`
- **Check**: Logs tab - look for download, transcription, or attribution errors
- **Causes**: Network issues, API failures, malformed RSS data

### Site Build Failures
- **Task**: `build-site`
- **Check**: Logs tab - look for "zensical build failed"
- **Causes**: Missing config, corrupted markdown, filesystem issues

### Deployment Failures
- **Task**: `deploy-site`
- **Check**: Logs tab - look for "rsync deployment failed"
- **Causes**: Permission issues, disk space, network problems

## Server-Side Logging

For more detailed system logs:

```bash
# Prefect server logs
sudo journalctl -u prefect-server -f

# Follow recent logs
sudo journalctl -u prefect-server -n 100 --no-pager

# Logs since specific time
sudo journalctl -u prefect-server --since "2026-01-25 09:00:00"
```

## Cron Job Failures

Check mail for cron output:

```bash
# List cron job emails
mail -H

# Read specific message
mail -N <message_number>
```

The cron job runs at 7:02 AM daily and sends email on failures.

## Log Retention

Prefect stores logs in its database. Configure retention in the Prefect server configuration if needed.

## Tips

1. **Use the search box** in the Logs tab to filter log messages
2. **Filter by log level** (INFO, ERROR, WARNING, DEBUG)
3. **Check task retries** - Failed tasks retry automatically (configured per-task)
4. **Look at timing** - Long gaps between log messages indicate slow operations
5. **Check concurrency limits** - Messages about "concurrency limits" are informational

## Quick Debugging Checklist

When a run fails:

1. ✅ Go to Prefect UI → Runs → Find the failed run
2. ✅ Check which task failed (Tasks tab - look for red/failed status)
3. ✅ Click on the failed task → Logs tab
4. ✅ Look for ERROR level messages
5. ✅ Check for subprocess output (STDOUT/STDERR sections)
6. ✅ Note any exception tracebacks
7. ✅ Check server logs if Prefect itself seems to be having issues

## Example: Debugging a Failed Build

```
# 1. Find the failed run in UI
http://webserver.phfactor.net:4200/runs

# 2. Click on "tgn-deploy" (or whatever failed)

# 3. Go to Tasks tab → See "build-site" is red/failed

# 4. Click "build-site" → Logs tab

# 5. Look for:
ERROR | Task run 'build-site-xxx' - zensical build failed with return code 1
ERROR | Task run 'build-site-xxx' - STDERR:
Error: No config file found in the current folder.

# 6. Fix: Check that mkdocs.yml exists in sites/tgn/
```

## Further Reading

- [Prefect Logging Documentation](https://docs.prefect.io/latest/guides/logs/)
- [Prefect UI Documentation](https://docs.prefect.io/latest/ui/overview/)
