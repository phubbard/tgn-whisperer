# Prefect Refactoring Plan

## Current Workflow Analysis

### Step 1: RSS Processing (process.py)
- Fetch RSS feeds for TGN, WCL, Hodinkee
- Process feeds to fill missing episode numbers (rss_processor)
- Check for new episodes (compare with {podcast}-notified.json)
- Send email notifications
- Create episode directories and JSON metadata files
- Update episodes.md indexes

### Step 2: Episode Processing (Makefile + episode_makefile)
For each episode:
- Download MP3 file
- Submit to Fluid Audio API for transcription
- Download episode HTML page
- Run Claude attribution (episode.py)
- Generate episode.md markdown
- Copy files to site directories

### Step 3: Site Generation (Makefile)
- Generate TGN shownotes (scrape Substack pages)
- Build static sites with zensical
- Generate search indexes with Pagefind
- Deploy via rsync

## Proposed Prefect Architecture

### Core Concepts
1. **Flows** = High-level workflows (one per podcast, plus site deployment)
2. **Tasks** = Individual operations (download MP3, transcribe, etc.)
3. **Artifacts** = Episode metadata, transcripts, etc.
4. **Caching** = Avoid re-downloading/re-transcribing
5. **Retries** = Handle transient failures (network, API rate limits)

### Flow Structure

```
Main Flow: Process All Podcasts
├── Sub-flow: Process TGN (runs independently)
│   ├── Task: Fetch RSS feed
│   ├── Task: Process feed (add episode numbers)
│   ├── Task: Check for new episodes
│   ├── Task: Send notifications
│   ├── For each new episode (parallel):
│   │   ├── Task: Create directories
│   │   ├── Task: Download MP3
│   │   ├── Task: Transcribe audio (Fluid Audio API - blocking)
│   │   ├── Task: Download episode HTML
│   │   ├── Task: Attribute speakers (Claude API)
│   │   └── Task: Generate markdown
│   └── If new episodes processed:
│       ├── Task: Generate TGN shownotes
│       ├── Task: Build TGN site (zensical)
│       ├── Task: Generate search index (Pagefind)
│       └── Task: Deploy TGN site (caddy2 static hosting)
│
├── Sub-flow: Process WCL (runs independently, same structure)
│   └── Includes WCL-specific site generation
│
└── Sub-flow: Process Hodinkee (runs independently, same structure)
    └── Includes Hodinkee-specific site generation
```

**Key Points:**
- All 3 podcast flows run in parallel
- Site generation happens immediately after each podcast completes (no waiting)
- Transcription calls are blocking (Mac Studio on LAN, no async needed)
- Static hosting via existing caddy2 setup with SSL


## Implementation Plan

### Phase 1: Setup Prefect Infrastructure
- [ ] Add prefect to pyproject.toml dependencies
- [ ] Set up Prefect server (local or cloud)
- [ ] Configure Prefect work pools
- [ ] Create prefect.yaml configuration
- [ ] Set up environment variables and secrets

### Phase 2: Create Task Functions
Convert existing functions into Prefect tasks:

**RSS & Episode Discovery Tasks:**
- [ ] `@task fetch_rss_feed(podcast: Podcast) -> str`
- [ ] `@task process_rss_feed(rss_content: str, podcast_name: str) -> dict`
- [ ] `@task check_new_episodes(podcast_name: str, current_eps: list) -> list`
- [ ] `@task send_notification_email(podcast: Podcast, new_eps: list)`

**Episode Processing Tasks:**
- [ ] `@task create_episode_directory(episode: Episode) -> Path`
- [ ] `@task download_mp3(episode: Episode) -> Path`
- [ ] `@task transcribe_audio(podcast: str, episode_num: float, mp3_path: Path) -> dict`
- [ ] `@task download_episode_html(episode: Episode) -> Path`
- [ ] `@task attribute_speakers(transcript: dict, podcast: str) -> dict`
- [ ] `@task generate_episode_markdown(episode: Episode, transcript: dict, speaker_map: dict) -> Path`

**Site Generation Tasks:**
- [ ] `@task generate_tgn_shownotes() -> Path`
- [ ] `@task generate_wcl_shownotes() -> Path`
- [ ] `@task build_site(podcast_name: str) -> Path`
- [ ] `@task generate_search_index(site_path: Path) -> bool`
- [ ] `@task deploy_site(podcast_name: str) -> bool`

### Phase 3: Create Flow Functions

**Main Orchestration Flow:**
```python
@flow(name="process-all-podcasts")
def process_all_podcasts():
    # Run all podcast processing flows in parallel
    # Each handles its own site generation independently
    tgn_future = process_podcast.submit(tgn_config)
    wcl_future = process_podcast.submit(wcl_config)
    hodinkee_future = process_podcast.submit(hodinkee_config)

    # Wait for completion (optional - could just fire and forget)
    tgn_future.wait()
    wcl_future.wait()
    hodinkee_future.wait()
```

**Podcast Processing Flow:**
```python
@flow(name="process-podcast")
def process_podcast(podcast: Podcast):
    # Fetch and process RSS
    rss_content = fetch_rss_feed(podcast)
    episodes_data = process_rss_feed(rss_content, podcast.name)

    # Check for new episodes
    new_eps = check_new_episodes(podcast.name, episodes_data)

    if not new_eps:
        return []

    # Send notifications
    send_notification_email(podcast, new_eps)

    # Process each new episode in parallel
    episode_futures = []
    for episode_data in new_eps:
        future = process_episode.submit(podcast, episode_data)
        episode_futures.append(future)

    # Wait for all episodes to complete
    results = [f.result() for f in episode_futures]

    # Generate and deploy this podcast's site immediately
    generate_and_deploy_site(podcast)

    return new_eps
```

**Site Generation Flow (per podcast):**
```python
@flow(name="generate-and-deploy-site")
def generate_and_deploy_site(podcast: Podcast):
    # Generate shownotes if applicable
    if podcast.name == 'tgn':
        generate_tgn_shownotes()
    elif podcast.name == 'wcl':
        generate_wcl_shownotes()

    # Build site with zensical
    site_path = build_site(podcast.name)

    # Generate search index
    generate_search_index(site_path)

    # Deploy to caddy2 (just updates static files in place)
    deploy_site(podcast.name, site_path)
```

**Episode Processing Flow:**
```python
@flow(name="process-episode")
def process_episode(podcast: Podcast, episode_data: dict):
    # Create episode object and directories
    episode = create_episode(episode_data)
    create_episode_directory(episode)

    # Download and transcribe (sequential, blocking call to Mac Studio)
    mp3_path = download_mp3(episode)
    transcript = transcribe_audio(podcast.name, episode.number, mp3_path)
    # Note: transcribe_audio blocks for 30-90 minutes, which is fine
    # since it's a LAN call to Mac Studio with Fluid Audio

    # Download HTML in parallel with attribution
    html_future = download_episode_html.submit(episode)
    speaker_map = attribute_speakers(transcript, podcast.name)
    html_path = html_future.result()

    # Generate final markdown
    md_path = generate_episode_markdown(episode, transcript, speaker_map)

    return md_path
```

### Phase 4: Task Configuration

**Retry Logic:**
- Network operations (RSS fetch, MP3 download): retry 3 times with exponential backoff
- API calls (transcription, Claude): retry 5 times with longer backoff
- File operations: retry 2 times

**Caching:**
- RSS feed parsing: cache for 5 minutes (avoid re-parsing during debugging)
- Episode metadata: cache indefinitely (doesn't change)
- Transcription results: cache indefinitely (expensive operation)

**Concurrency:**
- Episode processing: unlimited parallelism within a podcast
- Podcast processing: process all 3 podcasts in parallel
- API calls: respect rate limits (use Prefect rate limiters)

### Phase 5: Migration Strategy

**Approach: Gradual Replacement**

1. **Week 1: Parallel Run**
   - Keep existing Makefile workflow
   - Add new Prefect flows that run alongside
   - Compare outputs for correctness
   - Don't replace production yet

2. **Week 2: Podcast-by-Podcast**
   - Switch TGN to Prefect (lowest risk, most tested)
   - Monitor for 3-5 days
   - Switch WCL
   - Monitor for 3-5 days
   - Switch Hodinkee

3. **Week 3: Full Cutover**
   - Disable Makefile workflows
   - Update documentation
   - Remove deprecated code

**Rollback Plan:**
- Keep Makefile and process.py for 1 month after cutover
- Simple rollback: comment out Prefect cron, uncomment Make cron
- All existing episode data remains compatible

### Phase 6: Testing Strategy

**Unit Tests:**
- [ ] Test each task function in isolation
- [ ] Mock external APIs (Fluid Audio, Claude)
- [ ] Test error handling and retries

**Integration Tests:**
- [ ] Test full episode processing flow with test data
- [ ] Test new episode detection logic
- [ ] Test parallel processing of multiple episodes

**End-to-End Tests:**
- [ ] Process a single real episode through full pipeline
- [ ] Verify site generation and deployment
- [ ] Test email notifications

### Phase 7: Monitoring & Observability

**Prefect Dashboard Features:**
- View all flow runs (past and current)
- See task execution times and bottlenecks
- Track failure rates and retry attempts
- Monitor API usage (transcription, Claude)

**Custom Metrics:**
- Episodes processed per day
- Transcription costs (API usage)
- Claude API costs
- Processing time per episode
- Failure rates by task type

**Alerting:**
- Email on flow failures
- Slack notifications for critical errors
- Weekly summary reports

## Benefits of Prefect Refactor

### Immediate Benefits
1. **Visibility**: See exactly what's running, what failed, why
2. **Debugging**: Replay failed tasks without re-running entire pipeline
3. **Parallelism**: Process episodes in parallel (huge time savings)
4. **Retry Logic**: Automatic retries for transient failures
5. **Caching**: Avoid expensive re-transcription during debugging

### Long-term Benefits
1. **Scalability**: Easy to add more podcasts
2. **Deployment**: Can deploy to cloud (fly.io, AWS, etc.)
3. **Scheduling**: Built-in cron/interval scheduling
4. **Testing**: Easier to test individual components
5. **Maintenance**: Clearer code organization

## File Structure After Refactor

```
app/
├── flows/
│   ├── __init__.py
│   ├── main.py              # Main orchestration flow
│   ├── podcast.py           # Podcast processing flow
│   └── episode.py           # Episode processing flow
├── tasks/
│   ├── __init__.py
│   ├── rss.py              # RSS fetching and parsing
│   ├── download.py         # MP3 and HTML downloads
│   ├── transcribe.py       # Fluid Audio API calls
│   ├── attribute.py        # Claude speaker attribution
│   ├── markdown.py         # Markdown generation
│   ├── shownotes.py        # Shownotes generation
│   ├── build.py            # Site building (zensical)
│   └── deploy.py           # rsync deployment
├── models/
│   ├── __init__.py
│   ├── podcast.py          # Podcast dataclass
│   └── episode.py          # Episode dataclass
├── utils/
│   ├── __init__.py
│   ├── email.py            # Email sending
│   └── notifications.py    # Notification helpers
└── legacy/
    ├── process.py          # Old code (deprecated)
    └── episode.py          # Old code (deprecated)

prefect.yaml                # Prefect configuration
deployments/                # Prefect deployments
```

## Dependencies to Add

```toml
dependencies = [
    # ... existing deps ...
    "prefect>=3.0",          # Core Prefect
    "prefect-email",         # Email blocks
    "prefect-shell",         # Shell command tasks
]
```

## Configuration

**prefect.yaml:**
```yaml
name: tgn-whisperer
prefect-version: 3.0.0

# Work pools
work-pools:
  - name: podcast-processing
    type: process
    concurrency: 10

# Deployments
deployments:
  - name: process-all-podcasts
    version: 1.0.0
    description: Main podcast processing workflow
    schedule:
      interval: 3600  # Run every hour
    work_pool: podcast-processing
    entrypoint: app/flows/main.py:process_all_podcasts
```

## Decisions Made

1. **Prefect Self-Hosted** ✅
   - Running Prefect server on local infrastructure
   - Full control, no cost, existing infrastructure

2. **Full Prefect Refactor** ✅
   - Remove all Makefiles
   - Pure Prefect orchestration for everything
   - Better visibility and debugging

3. **Blocking Transcription Calls** ✅
   - Mac Studio on LAN handles transcription
   - Blocking calls are fine (30-90 minutes)
   - No async/polling needed for LAN operations

4. **Independent Site Generation** ✅
   - Each podcast generates/deploys its site immediately after processing
   - No waiting for all podcasts to complete
   - Caddy2 provides static hosting with SSL

5. **Deployment Platform** ✅
   - Stay on current infrastructure
   - Caddy2 for static hosting
   - Prefect server on same machine

## Next Steps

1. Review this plan and approve/modify
2. Set up Prefect (local server or cloud account)
3. Start with Phase 1: Basic infrastructure
4. Create one task as proof of concept
5. Build out flows incrementally

## References

- [Prefect Documentation](https://docs.prefect.io/)
- [Verdad project](https://github.com/user/verdad) - Similar Prefect usage mentioned in issue
- [GitHub Issue #3](https://github.com/phubbard/tgn-whisperer/issues/3)
