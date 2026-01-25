# TGN Whisperer Usage

## Setup

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

## Running the Pipeline

The system uses Prefect 3.0 for workflow orchestration:

```bash
# Run full workflow (all 3 podcasts)
uv run python app/run_prefect.py

# Run individual podcasts
uv run python app/run_tgn.py
uv run python app/run_wcl.py
uv run python app/run_hodinkee.py

# Run tests
uv run pytest app/ -v

# Process a single RSS feed to add missing episode numbers
uv run python app/rss_processor.py app/test_feeds/tgn.rss

# Reprocess specific episode
./reprocess tgn 14 --all --make          # Full reprocess
./reprocess wcl 100 --attribute --make   # Just re-attribute speakers
./reprocess tgn 361 --all --dry-run      # Preview without executing
```

## Why uv?

- **Fast**: 10-100x faster than pip
- **Reliable**: Reproducible installs with lock file
- **Simple**: No need to activate/deactivate venvs
- **All-in-one**: Replaces pip, pip-tools, pipx, poetry, pyenv

## Migration Notes

- Old: `requirements.txt` → New: `pyproject.toml`
- Old: `source venv/bin/activate` → New: `uv run`
- Old venv in `venv/` → New venv in `.venv/`
- The old `venv/` directory can be safely deleted
