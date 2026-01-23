# Prefect Setup and Usage

This directory contains the Prefect-based podcast processing pipeline.

## Directory Structure

```
app/
├── flows/               # Prefect flow definitions
│   ├── main.py         # Main orchestration flow
│   ├── podcast.py      # Podcast processing flow
│   └── episode.py      # Episode processing flow
├── tasks/              # Prefect task definitions (TODO)
│   ├── rss.py         # RSS fetching and parsing
│   ├── download.py    # MP3 and HTML downloads
│   ├── transcribe.py  # Fluid Audio API calls
│   ├── attribute.py   # Claude speaker attribution
│   ├── markdown.py    # Markdown generation
│   ├── shownotes.py   # Shownotes generation
│   ├── build.py       # Site building (zensical)
│   └── deploy.py      # rsync deployment
├── models/             # Data models
│   ├── podcast.py     # Podcast dataclass
│   └── episode.py     # Episode dataclass
├── utils/              # Utility functions (TODO)
│   ├── email.py       # Email sending
│   └── notifications.py
└── legacy/             # Old code (will be deprecated)
    ├── process.py
    └── episode.py
```

## Getting Started

### 1. Install Dependencies

Dependencies are already installed via `uv sync`. The following Prefect packages are included:
- `prefect>=3.0` - Core Prefect
- `prefect-email` - Email notifications
- `prefect-shell` - Shell command tasks

### 2. Start Prefect Server (Local)

Start the Prefect server locally:

```bash
prefect server start
```

This will start the server at http://127.0.0.1:4200

### 3. Configure Work Pool

Create a work pool for podcast processing:

```bash
prefect work-pool create podcast-processing --type process
```

### 4. Start a Worker

Start a worker to execute flows:

```bash
prefect worker start --pool podcast-processing
```

### 5. Run Flows

#### Run Locally (Development)

Test flows locally without deploying:

```bash
# Run main orchestration flow
uv run python app/flows/main.py
```

#### Deploy and Schedule

Deploy flows to Prefect server:

```bash
prefect deploy --all
```

This will deploy all flows defined in `prefect.yaml` with their schedules.

## Current Implementation Status

### Phase 1: Infrastructure Setup ✅
- [x] Add Prefect dependencies
- [x] Create directory structure
- [x] Create prefect.yaml configuration
- [x] Define data models (Podcast, Episode)
- [x] Create flow skeletons

### Phase 2: Task Implementation (TODO)
- [ ] Convert RSS processing to tasks
- [ ] Convert download logic to tasks
- [ ] Convert transcription to tasks
- [ ] Convert speaker attribution to tasks
- [ ] Convert markdown generation to tasks
- [ ] Convert site building to tasks

### Phase 3: Flow Implementation (TODO)
- [ ] Complete podcast processing flow
- [ ] Complete episode processing flow
- [ ] Add error handling and retries
- [ ] Add caching configuration

## Architecture

### Flow Hierarchy

```
process_all_podcasts (main.py)
├── process_podcast (podcast.py) [parallel for TGN, WCL, Hodinkee]
│   ├── process_episode (episode.py) [parallel for each new episode]
│   └── generate_and_deploy_site (podcast.py) [runs after episodes complete]
```

### Key Design Decisions

1. **Parallel Processing**: All 3 podcasts process in parallel
2. **Independent Deployment**: Each podcast deploys its site immediately after processing
3. **Blocking Transcription**: Transcription calls to Mac Studio are blocking (30-90 min)
4. **Self-Hosted**: Prefect server runs locally
5. **Static Hosting**: Sites served via caddy2 with SSL

## Testing

Run a test flow locally:

```bash
uv run python app/flows/main.py
```

View the flow run in the Prefect UI at http://127.0.0.1:4200

## Next Steps

1. Implement RSS processing tasks (Phase 2)
2. Test with single podcast (TGN)
3. Gradually migrate remaining functionality
4. Run parallel with Make for validation
5. Complete cutover

See `PREFECT_REFACTOR_PLAN.md` for full implementation plan.
