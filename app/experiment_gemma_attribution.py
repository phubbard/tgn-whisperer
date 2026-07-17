#!/usr/bin/env python3
"""
Experiment: Compare Claude vs Gemma 4 31B for speaker attribution and synopsis.

Sends the same transcript chunks and prompt to both Claude (via Anthropic API)
and Gemma 4 31B (via LM Studio's OpenAI-compatible API on axiom.phfactor.net),
then generates an HTML comparison report.
"""
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from constants import CLAUDE_MODEL, CLAUDE_MAX_TOKENS

# Configuration
LM_STUDIO_URL = "http://axiom.phfactor.net:1234/v1/chat/completions"
GEMMA_MODEL = "google/gemma-4-31b"

# Same prompt used by the production attribution system
ATTRIBUTION_PROMPT = '''The following is a podcast transcript. Analyze it and return:

1. A JSON speaker attribution block wrapped in <attribution> tags, mapping each speaker ID to their name:
<attribution>
{"SPEAKER_00": "Name", "SPEAKER_01": "Name"}
</attribution>

2. A two to four paragraph synopsis wrapped in <synopsis> tags:
<synopsis>
Synopsis text here.
</synopsis>

If you can't determine a speaker's name, use "Unknown".
'''

# 10 TGN episodes: mix of early, mid, recent, guests
TEST_EPISODES = [1, 6, 15, 44, 165, 200, 300, 360, 363, 367]


def load_episode_data(ep_num):
    """Load transcript chunks and existing Claude results for an episode."""
    ep_dir = Path(f"podcasts/tgn/{ep_num}")
    if not ep_dir.exists():
        return None

    wo_path = ep_dir / "whisper-output.json"
    sm_path = ep_dir / "speaker-map.json"
    syn_path = ep_dir / "synopsis.txt"

    if not wo_path.exists():
        return None

    chunks = json.loads(wo_path.read_text())
    transcript_text = json.dumps(chunks)

    claude_speaker_map = {}
    if sm_path.exists():
        claude_speaker_map = json.loads(sm_path.read_text())

    claude_synopsis = ""
    if syn_path.exists():
        claude_synopsis = syn_path.read_text()

    # Get episode title from episode.md
    md_path = ep_dir / "episode.md"
    title = f"Episode {ep_num}"
    if md_path.exists():
        for line in md_path.read_text().split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break

    return {
        'ep_num': ep_num,
        'title': title,
        'transcript_text': transcript_text,
        'chunks': chunks,
        'claude_speaker_map': claude_speaker_map,
        'claude_synopsis': claude_synopsis,
    }


def parse_response(text):
    """Parse attribution and synopsis from LLM response text."""
    # Parse speaker map
    attr_match = re.search(r'<attribution>\s*(\{.*?\})\s*</attribution>', text, re.DOTALL)
    speaker_map = {}
    if attr_match:
        try:
            speaker_map = json.loads(attr_match.group(1))
        except json.JSONDecodeError:
            for line in attr_match.group(1).split('\n'):
                m = re.search(r'"(SPEAKER_\d+)"\s*:\s*"([^"]+)"', line)
                if m:
                    speaker_map[m.group(1)] = m.group(2)

    # Parse synopsis
    syn_match = re.search(r'<synopsis>\s*(.*?)\s*</synopsis>', text, re.DOTALL)
    synopsis = syn_match.group(1) if syn_match else "Synopsis not found in response."

    return speaker_map, synopsis


def call_gemma(transcript_text):
    """Call Gemma 4 31B via LM Studio's OpenAI-compatible API."""
    payload = {
        "model": GEMMA_MODEL,
        "messages": [
            {"role": "system", "content": ATTRIBUTION_PROMPT},
            {"role": "user", "content": transcript_text},
        ],
        "max_tokens": 16384,
        "temperature": 0.3,
    }

    start = time.time()
    resp = requests.post(LM_STUDIO_URL, json=payload, timeout=1200)
    elapsed = time.time() - start

    if resp.status_code != 200:
        return None, None, elapsed, f"HTTP {resp.status_code}: {resp.text[:200]}"

    data = resp.json()
    msg = data['choices'][0]['message']
    # Gemma 4 is a thinking model - response may be in content or reasoning_content
    result_text = msg.get('content', '') or ''
    reasoning = msg.get('reasoning_content', '') or ''

    # If content is empty but reasoning has the tags, use reasoning
    if not result_text.strip() and reasoning:
        result_text = reasoning
    # If tags are split across both, concatenate
    elif '<attribution>' not in result_text and '<attribution>' in reasoning:
        result_text = reasoning + '\n' + result_text

    speaker_map, synopsis = parse_response(result_text)

    return speaker_map, synopsis, elapsed, result_text


def compare_speaker_maps(claude_map, gemma_map):
    """Compare two speaker maps and return accuracy info."""
    all_keys = set(list(claude_map.keys()) + list(gemma_map.keys()))
    matches = 0
    mismatches = []

    for key in sorted(all_keys):
        claude_val = claude_map.get(key, "(missing)")
        gemma_val = gemma_map.get(key, "(missing)")
        if claude_val.lower().strip() == gemma_val.lower().strip():
            matches += 1
        else:
            mismatches.append((key, claude_val, gemma_val))

    total = len(all_keys)
    accuracy = matches / total * 100 if total > 0 else 0
    return accuracy, matches, total, mismatches


def generate_html(results):
    """Generate HTML comparison report."""
    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Claude vs Gemma 4 31B — Attribution Comparison</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
  h1 { color: #333; border-bottom: 2px solid #666; padding-bottom: 10px; }
  h2 { color: #444; margin-top: 40px; }
  .episode { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
  .episode h3 { margin-top: 0; color: #222; }
  .meta { color: #888; font-size: 0.9em; margin-bottom: 15px; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; }
  th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  th { background: #f0f0f0; font-weight: 600; }
  .match { background: #e8f5e9; }
  .mismatch { background: #fce4ec; }
  .synopsis { background: #fafafa; padding: 15px; border-left: 3px solid #ccc; margin: 10px 0; font-size: 0.95em; line-height: 1.6; }
  .synopsis.claude { border-left-color: #7c4dff; }
  .synopsis.gemma { border-left-color: #00897b; }
  .label { font-weight: 600; margin-bottom: 5px; }
  .label.claude { color: #7c4dff; }
  .label.gemma { color: #00897b; }
  .summary-box { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
  .accuracy { font-size: 1.3em; font-weight: bold; }
  .accuracy.good { color: #2e7d32; }
  .accuracy.ok { color: #f57f17; }
  .accuracy.bad { color: #c62828; }
  .error { background: #fce4ec; padding: 10px; border-radius: 4px; color: #c62828; }
  .timing { color: #666; font-size: 0.85em; }
</style>
</head>
<body>
"""
    html += f"<h1>Claude vs Gemma 4 31B — Speaker Attribution Comparison</h1>\n"
    html += f"<p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>\n"
    html += f"<p>Claude model: <code>{CLAUDE_MODEL}</code> &nbsp;|&nbsp; Gemma model: <code>{GEMMA_MODEL}</code></p>\n"

    # Summary stats
    total_accuracy = []
    total_gemma_time = 0
    errors = 0

    for r in results:
        if r.get('error'):
            errors += 1
        else:
            total_accuracy.append(r['accuracy'])
            total_gemma_time += r['gemma_elapsed']

    avg_accuracy = sum(total_accuracy) / len(total_accuracy) if total_accuracy else 0
    acc_class = 'good' if avg_accuracy >= 90 else ('ok' if avg_accuracy >= 70 else 'bad')

    html += '<div class="summary-box">\n'
    html += f'<h2 style="margin-top:0">Summary</h2>\n'
    html += f'<p class="accuracy {acc_class}">Overall Speaker Map Accuracy: {avg_accuracy:.1f}%</p>\n'
    avg_time = total_gemma_time / len(total_accuracy) if total_accuracy else 0
    html += f'<p>Episodes tested: {len(results)} &nbsp;|&nbsp; Errors: {errors} &nbsp;|&nbsp; Avg Gemma response time: {avg_time:.1f}s</p>\n'
    html += '</div>\n'

    # Per-episode results
    for r in results:
        html += '<div class="episode">\n'
        html += f'<h3>Episode {r["ep_num"]}: {escape(r["title"])}</h3>\n'
        html += f'<div class="meta">{r["chunk_count"]} chunks, {r["text_len"]//1000}k characters</div>\n'

        if r.get('error'):
            html += f'<div class="error">Error: {escape(r["error"])}</div>\n'
            html += '</div>\n'
            continue

        # Speaker map comparison table
        html += f'<div class="timing">Gemma response time: {r["gemma_elapsed"]:.1f}s</div>\n'
        acc_class = 'good' if r['accuracy'] >= 90 else ('ok' if r['accuracy'] >= 70 else 'bad')
        html += f'<p>Speaker map accuracy: <span class="accuracy {acc_class}">{r["accuracy"]:.0f}%</span> ({r["matches"]}/{r["total"]})</p>\n'

        html += '<table>\n<tr><th>Speaker ID</th><th>Claude</th><th>Gemma</th><th>Match</th></tr>\n'
        all_keys = sorted(set(list(r['claude_map'].keys()) + list(r['gemma_map'].keys())))
        for key in all_keys:
            cv = r['claude_map'].get(key, "(missing)")
            gv = r['gemma_map'].get(key, "(missing)")
            match = cv.lower().strip() == gv.lower().strip()
            row_class = 'match' if match else 'mismatch'
            check = '✓' if match else '✗'
            html += f'<tr class="{row_class}"><td>{escape(key)}</td><td>{escape(cv)}</td><td>{escape(gv)}</td><td>{check}</td></tr>\n'
        html += '</table>\n'

        # Synopsis comparison
        html += '<div class="label claude">Claude Synopsis:</div>\n'
        html += f'<div class="synopsis claude">{escape(r["claude_synopsis"])}</div>\n'
        html += '<div class="label gemma">Gemma Synopsis:</div>\n'
        html += f'<div class="synopsis gemma">{escape(r["gemma_synopsis"])}</div>\n'

        html += '</div>\n'

    html += "</body>\n</html>\n"
    return html


def main():
    results = []

    for i, ep_num in enumerate(TEST_EPISODES):
        print(f"[{i+1}/{len(TEST_EPISODES)}] Processing episode {ep_num}...", flush=True)

        data = load_episode_data(ep_num)
        if data is None:
            print(f"  Skipping: no data found", flush=True)
            results.append({
                'ep_num': ep_num, 'title': f'Episode {ep_num}',
                'chunk_count': 0, 'text_len': 0,
                'error': 'Episode data not found'
            })
            continue

        print(f"  Title: {data['title'][:60]}", flush=True)
        print(f"  Transcript: {len(data['chunks'])} chunks, {len(data['transcript_text'])//1000}k chars", flush=True)

        # Call Gemma
        print(f"  Calling Gemma...", flush=True)
        gemma_map, gemma_synopsis, elapsed, raw_response = call_gemma(data['transcript_text'])

        result = {
            'ep_num': ep_num,
            'title': data['title'],
            'chunk_count': len(data['chunks']),
            'text_len': len(data['transcript_text']),
            'claude_map': data['claude_speaker_map'],
            'claude_synopsis': data['claude_synopsis'],
        }

        if gemma_map is None:
            result['error'] = raw_response
            print(f"  ERROR: {raw_response}", flush=True)
        else:
            accuracy, matches, total, mismatches = compare_speaker_maps(
                data['claude_speaker_map'], gemma_map
            )
            result.update({
                'gemma_map': gemma_map,
                'gemma_synopsis': gemma_synopsis,
                'gemma_elapsed': elapsed,
                'accuracy': accuracy,
                'matches': matches,
                'total': total,
                'mismatches': mismatches,
            })
            print(f"  Gemma: {elapsed:.1f}s, accuracy: {accuracy:.0f}% ({matches}/{total})", flush=True)
            if mismatches:
                for key, cv, gv in mismatches:
                    print(f"    {key}: Claude='{cv}' vs Gemma='{gv}'", flush=True)

        results.append(result)

    # Generate HTML report
    output_path = Path("gemma_comparison.html")
    html = generate_html(results)
    output_path.write_text(html)
    print(f"\nReport written to {output_path.resolve()}", flush=True)


if __name__ == '__main__':
    main()
