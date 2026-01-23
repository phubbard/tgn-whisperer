# TGN Whisperer Usage

## Setup

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

## Running the Pipeline

Replace the old `source venv/bin/activate && make` with:

```bash
uv run make
```

## Common Commands

```bash
# Run the full processing pipeline
uv run make

# Process RSS feeds and create episode directories
uv run python app/process.py

# Process a single RSS feed to add missing episode numbers
uv run python app/rss_processor.py app/test_feeds/tgn.rss

# Run tests
uv run pytest app/test_rss_processing.py -v

# Run any Python script with dependencies available
uv run python app/your_script.py
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
