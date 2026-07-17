#!/usr/bin/env python3
"""
Generate traffic analytics HTML dashboard from Caddy JSON access logs.

Processes current and rotated log files for tgn.phfactor.net, producing
a self-contained HTML page with charts and tables showing:
- Daily/weekly/monthly traffic trends
- Unique visitors (by IP)
- Popular pages (episode pages vs assets)
- Top referrers
- Bots/crawlers vs human traffic
- Geographic distribution (via Cloudflare country headers)
- User agent breakdown (browser, OS, device)
"""
import gzip
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from html import escape
from pathlib import Path

LOG_DIR = Path("/var/log/caddy")
LOG_PREFIX = "tgn"  # matches tgn.log and tgn-*.log.gz

# Known bot patterns in User-Agent strings
BOT_PATTERNS = [
    r'bot\b', r'crawl', r'spider', r'slurp', r'Googlebot', r'bingbot',
    r'Baiduspider', r'YandexBot', r'DuckDuckBot', r'Sogou', r'Exabot',
    r'facebot', r'facebookexternalhit', r'ia_archiver', r'MJ12bot',
    r'SemrushBot', r'AhrefsBot', r'DotBot', r'PetalBot', r'Bytespider',
    r'GPTBot', r'ClaudeBot', r'Claude-Web', r'Applebot', r'Amazonbot',
    r'anthropic', r'CCBot', r'DataForSeoBot', r'Screaming Frog',
    r'HeadlessChrome', r'PhantomJS', r'Selenium', r'Scrapy',
    r'python-requests', r'urllib', r'httpx', r'curl/', r'wget/',
    r'Go-http-client', r'Java/', r'libwww', r'lwp-trivial',
    r'Mediapartners', r'APIs-Google', r'AdsBot', r'Feedfetcher',
    r'LinkedInBot', r'Twitterbot', r'WhatsApp', r'Slackbot',
    r'TelegramBot', r'Discordbot', r'archive\.org_bot', r'Nutch',
    r'CensysInspect', r'Nmap', r'masscan', r'ZmEu', r'Nikto',
    r'sqlmap', r'Acunetix', r'BLEXBot', r'Mail\.RU_Bot',
    r'coccocbot', r'SeekportBot', r'Qwantify', r'Pinterestbot',
    r'UptimeRobot', r'StatusCake', r'Pingdom', r'Site24x7',
    r'thesis-research', r'NetcraftSurveyAgent', r'CriteoBot',
]
BOT_RE = re.compile('|'.join(BOT_PATTERNS), re.IGNORECASE)

# Asset file extensions to filter from "page" views
ASSET_EXTENSIONS = {
    '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
    '.woff', '.woff2', '.ttf', '.eot', '.map', '.json', '.xml',
}


def is_bot(user_agent: str) -> bool:
    return bool(BOT_RE.search(user_agent))


def is_asset(uri: str) -> bool:
    lower = uri.lower().split('?')[0]
    return any(lower.endswith(ext) for ext in ASSET_EXTENSIONS)


def is_page_view(uri: str) -> bool:
    """A page view is a non-asset request that returns HTML content."""
    if is_asset(uri):
        return False
    # pagefind chunks
    if '/pagefind/' in uri:
        return False
    return True


def parse_episode_from_uri(uri: str):
    """Extract episode number from URI like /363/episode/ or /363.0/episode/."""
    m = re.match(r'^/(\d+(?:\.\d+)?)/episode/?$', uri)
    if m:
        num = m.group(1)
        # Normalize: strip .0 suffix (123.0 -> 123) but keep real fractionals (14.5)
        if '.' in num:
            try:
                f = float(num)
                if f == int(f):
                    return str(int(f))
            except ValueError:
                pass
        return num
    return None


def classify_bot(user_agent: str) -> str:
    """Classify a bot by name."""
    ua_lower = user_agent.lower()

    classifiers = [
        ('Googlebot', r'googlebot'),
        ('Bingbot', r'bingbot'),
        ('Applebot', r'applebot'),
        ('GPTBot', r'gptbot'),
        ('ClaudeBot', r'claudebot|claude-web|anthropic'),
        ('Amazonbot', r'amazonbot'),
        ('AhrefsBot', r'ahrefsbot'),
        ('SemrushBot', r'semrushbot'),
        ('Bytespider', r'bytespider'),
        ('PetalBot', r'petalbot'),
        ('YandexBot', r'yandexbot'),
        ('DuckDuckBot', r'duckduckbot'),
        ('Facebookbot', r'facebot|facebookexternalhit'),
        ('Slackbot', r'slackbot'),
        ('Twitterbot', r'twitterbot'),
        ('CCBot', r'ccbot'),
        ('DataForSeoBot', r'dataforseobot'),
        ('DotBot', r'dotbot'),
        ('MJ12bot', r'mj12bot'),
        ('UptimeRobot', r'uptimerobot'),
        ('Python/requests', r'python-requests|httpx|urllib'),
        ('curl/wget', r'curl/|wget/'),
    ]
    for name, pattern in classifiers:
        if re.search(pattern, ua_lower):
            return name
    return 'Other Bot'


def parse_os_device(user_agent: str) -> tuple[str, str]:
    """Extract OS and device type from User-Agent."""
    ua = user_agent

    # Device
    if 'iPhone' in ua or 'iPod' in ua:
        device = 'iPhone'
    elif 'iPad' in ua:
        device = 'iPad'
    elif 'Android' in ua and 'Mobile' in ua:
        device = 'Android Phone'
    elif 'Android' in ua:
        device = 'Android Tablet'
    elif 'Macintosh' in ua:
        device = 'Mac'
    elif 'Windows' in ua:
        device = 'Windows'
    elif 'Linux' in ua:
        device = 'Linux'
    elif 'CrOS' in ua:
        device = 'ChromeOS'
    else:
        device = 'Other'

    # Browser
    if 'Safari' in ua and 'Chrome' not in ua and 'Chromium' not in ua:
        browser = 'Safari'
    elif 'Firefox' in ua:
        browser = 'Firefox'
    elif 'Edg/' in ua:
        browser = 'Edge'
    elif 'Chrome' in ua or 'Chromium' in ua or 'CriOS' in ua:
        browser = 'Chrome'
    elif 'Opera' in ua or 'OPR/' in ua:
        browser = 'Opera'
    else:
        browser = 'Other'

    return device, browser


def load_logs():
    """Load all TGN log files (current + rotated archives)."""
    records = []

    log_files = sorted(LOG_DIR.glob(f"{LOG_PREFIX}-*.log.gz"))
    current = LOG_DIR / f"{LOG_PREFIX}.log"
    if current.exists():
        log_files.append(current)

    for log_file in log_files:
        opener = gzip.open if log_file.suffix == '.gz' else open
        try:
            with opener(log_file, 'rt', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except (PermissionError, OSError) as e:
            print(f"Skipping {log_file}: {e}")

    return records


def analyze(records):
    """Analyze log records and return stats dict."""
    stats = {
        'total_requests': 0,
        'total_bytes': 0,
        'first_date': None,
        'last_date': None,

        # Daily counts
        'daily_requests': Counter(),
        'daily_uniques': defaultdict(set),
        'daily_page_views': Counter(),
        'daily_bot_requests': Counter(),

        # Weekly counts
        'weekly_requests': Counter(),
        'weekly_uniques': defaultdict(set),

        # Pages
        'page_views': Counter(),
        'episode_views': Counter(),

        # Visitors
        'all_ips': set(),
        'human_ips': set(),

        # Referrers
        'referrers': Counter(),

        # Bots
        'bot_requests': 0,
        'bot_names': Counter(),

        # Geo
        'countries': Counter(),

        # User agents
        'devices': Counter(),
        'browsers': Counter(),

        # Status codes
        'status_codes': Counter(),

        # Hourly distribution
        'hourly': Counter(),
    }

    for rec in records:
        ts = rec.get('ts', 0)
        dt = datetime.fromtimestamp(ts)
        date_str = dt.strftime('%Y-%m-%d')
        week_str = dt.strftime('%Y-W%W')
        hour = dt.hour

        req = rec.get('request', {})
        uri = req.get('uri', '')
        method = req.get('method', '')
        headers = req.get('headers', {})
        status = rec.get('status', 0)
        size = rec.get('size', 0)

        # Real client IP from Cloudflare, fallback to remote_ip
        cf_ip_list = headers.get('Cf-Connecting-Ip', [])
        client_ip = cf_ip_list[0] if cf_ip_list else req.get('remote_ip', 'unknown')

        ua_list = headers.get('User-Agent', [''])
        user_agent = ua_list[0] if ua_list else ''

        country_list = headers.get('Cf-Ipcountry', ['??'])
        country = country_list[0] if country_list else '??'

        referer_list = headers.get('Referer', [])
        referer = referer_list[0] if referer_list else ''

        if stats['first_date'] is None or dt < stats['first_date']:
            stats['first_date'] = dt
        if stats['last_date'] is None or dt > stats['last_date']:
            stats['last_date'] = dt

        stats['total_requests'] += 1
        stats['total_bytes'] += size
        stats['status_codes'][status] += 1
        stats['all_ips'].add(client_ip)
        stats['hourly'][hour] += 1

        bot = is_bot(user_agent)

        if bot:
            stats['bot_requests'] += 1
            stats['bot_names'][classify_bot(user_agent)] += 1
            stats['daily_bot_requests'][date_str] += 1
        else:
            stats['human_ips'].add(client_ip)
            stats['countries'][country] += 1
            device, browser = parse_os_device(user_agent)
            stats['devices'][device] += 1
            stats['browsers'][browser] += 1

        stats['daily_requests'][date_str] += 1
        stats['daily_uniques'][date_str].add(client_ip)
        stats['weekly_requests'][week_str] += 1
        stats['weekly_uniques'][week_str].add(client_ip)

        if method == 'GET' and is_page_view(uri):
            stats['daily_page_views'][date_str] += 1
            stats['page_views'][uri] += 1

            ep = parse_episode_from_uri(uri)
            if ep:
                stats['episode_views'][ep] += 1

        # Referrer analysis (skip self-referrals and empty)
        if referer and 'tgn.phfactor.net' not in referer:
            # Simplify to domain
            m = re.match(r'https?://([^/]+)', referer)
            if m:
                domain = m.group(1).lower()
                stats['referrers'][domain] += 1

    return stats


def generate_html(stats):
    """Generate self-contained HTML analytics dashboard."""
    days = (stats['last_date'] - stats['first_date']).days + 1
    human_pct = (1 - stats['bot_requests'] / stats['total_requests']) * 100 if stats['total_requests'] else 0

    # Prepare daily data for chart
    all_dates = sorted(stats['daily_requests'].keys())
    daily_labels = json.dumps(all_dates)
    daily_requests = json.dumps([stats['daily_requests'][d] for d in all_dates])
    daily_uniques = json.dumps([len(stats['daily_uniques'][d]) for d in all_dates])
    daily_pages = json.dumps([stats['daily_page_views'].get(d, 0) for d in all_dates])
    daily_bots = json.dumps([stats['daily_bot_requests'].get(d, 0) for d in all_dates])

    # Weekly data
    all_weeks = sorted(stats['weekly_requests'].keys())
    weekly_labels = json.dumps(all_weeks)
    weekly_requests = json.dumps([stats['weekly_requests'][w] for w in all_weeks])
    weekly_uniques = json.dumps([len(stats['weekly_uniques'][w]) for w in all_weeks])

    # Hourly data
    hourly_data = json.dumps([stats['hourly'].get(h, 0) for h in range(24)])

    # Top episodes
    top_episodes = stats['episode_views'].most_common(30)

    # Top pages (non-episode)
    top_pages = [(uri, count) for uri, count in stats['page_views'].most_common(20)
                 if not parse_episode_from_uri(uri)]

    # Top referrers
    top_referrers = stats['referrers'].most_common(20)

    # Top bots
    top_bots = stats['bot_names'].most_common(20)

    # Top countries
    top_countries = stats['countries'].most_common(20)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>TGN Whisperer — Traffic Analytics</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f5f5f5; color: #333; }}
  h1 {{ border-bottom: 2px solid #444; padding-bottom: 10px; }}
  h2 {{ margin-top: 40px; color: #444; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
  .stat-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
  .stat-card .value {{ font-size: 2em; font-weight: bold; color: #222; }}
  .stat-card .label {{ color: #888; font-size: 0.9em; margin-top: 5px; }}
  .chart-container {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 900px) {{ .chart-row {{ grid-template-columns: 1fr; }} }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #f0f0f0; font-weight: 600; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  td:last-child {{ text-align: right; }}
  .table-container {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .tables-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 900px) {{ .tables-row {{ grid-template-columns: 1fr; }} }}
  .bar {{ background: #4a90d9; height: 18px; border-radius: 3px; min-width: 2px; }}
  .generated {{ color: #999; font-size: 0.85em; margin-top: 30px; }}
</style>
</head>
<body>

<h1>TGN Whisperer — Traffic Analytics</h1>
<p>Data from {stats['first_date'].strftime('%B %d, %Y')} to {stats['last_date'].strftime('%B %d, %Y')} ({days} days)</p>

<div class="stats-grid">
  <div class="stat-card"><div class="value">{stats['total_requests']:,}</div><div class="label">Total Requests</div></div>
  <div class="stat-card"><div class="value">{stats['total_requests'] - stats['bot_requests']:,}</div><div class="label">Human Requests</div></div>
  <div class="stat-card"><div class="value">{len(stats['all_ips']):,}</div><div class="label">Unique IPs (all)</div></div>
  <div class="stat-card"><div class="value">{len(stats['human_ips']):,}</div><div class="label">Unique IPs (human)</div></div>
  <div class="stat-card"><div class="value">{stats['total_bytes'] / 1024 / 1024 / 1024:.1f} GB</div><div class="label">Data Served</div></div>
  <div class="stat-card"><div class="value">{stats['bot_requests']:,}</div><div class="label">Bot Requests ({human_pct:.0f}% human)</div></div>
  <div class="stat-card"><div class="value">{sum(stats['daily_page_views'].values()):,}</div><div class="label">Page Views</div></div>
  <div class="stat-card"><div class="value">{len(stats['episode_views']):,}</div><div class="label">Episodes Viewed</div></div>
</div>

<h2>Daily Traffic</h2>
<div class="chart-container">
  <canvas id="dailyChart" height="100"></canvas>
</div>

<h2>Weekly Traffic</h2>
<div class="chart-container">
  <canvas id="weeklyChart" height="80"></canvas>
</div>

<div class="chart-row">
  <div class="chart-container">
    <h3 style="margin-top:0">Hourly Distribution (UTC)</h3>
    <canvas id="hourlyChart" height="120"></canvas>
  </div>
  <div class="chart-container">
    <h3 style="margin-top:0">Bots vs Humans (daily)</h3>
    <canvas id="botChart" height="120"></canvas>
  </div>
</div>

<h2>Most Popular Episodes</h2>
<div class="table-container">
<table>
<tr><th>#</th><th>Episode</th><th>Views</th><th></th></tr>
"""
    max_ep_views = top_episodes[0][1] if top_episodes else 1
    for i, (ep, count) in enumerate(top_episodes, 1):
        bar_w = count / max_ep_views * 100
        html += f'<tr><td>{i}</td><td><a href="https://tgn.phfactor.net/{ep}/episode/">{ep}</a></td><td>{count:,}</td><td><div class="bar" style="width:{bar_w:.0f}%"></div></td></tr>\n'
    html += "</table>\n</div>\n"

    html += """
<div class="tables-row">
<div class="table-container">
<h3 style="margin-top:0">Top Pages (non-episode)</h3>
<table><tr><th>Page</th><th>Views</th></tr>
"""
    for uri, count in top_pages:
        html += f'<tr><td>{escape(uri)}</td><td>{count:,}</td></tr>\n'
    html += "</table>\n</div>\n"

    html += """
<div class="table-container">
<h3 style="margin-top:0">Top Referrers</h3>
<table><tr><th>Domain</th><th>Requests</th></tr>
"""
    for domain, count in top_referrers:
        html += f'<tr><td>{escape(domain)}</td><td>{count:,}</td></tr>\n'
    html += "</table>\n</div>\n</div>\n"

    html += """
<div class="tables-row">
<div class="table-container">
<h3 style="margin-top:0">Bots &amp; Crawlers</h3>
<table><tr><th>Bot</th><th>Requests</th></tr>
"""
    for name, count in top_bots:
        html += f'<tr><td>{escape(name)}</td><td>{count:,}</td></tr>\n'
    html += "</table>\n</div>\n"

    html += """
<div class="table-container">
<h3 style="margin-top:0">Countries (human traffic)</h3>
<table><tr><th>Country</th><th>Requests</th></tr>
"""
    for country, count in top_countries:
        html += f'<tr><td>{escape(country)}</td><td>{count:,}</td></tr>\n'
    html += "</table>\n</div>\n</div>\n"

    html += """
<div class="tables-row">
<div class="table-container">
<h3 style="margin-top:0">Devices (human traffic)</h3>
<table><tr><th>Device</th><th>Requests</th></tr>
"""
    for device, count in stats['devices'].most_common(10):
        html += f'<tr><td>{escape(device)}</td><td>{count:,}</td></tr>\n'
    html += "</table>\n</div>\n"

    html += """
<div class="table-container">
<h3 style="margin-top:0">Browsers (human traffic)</h3>
<table><tr><th>Browser</th><th>Requests</th></tr>
"""
    for browser, count in stats['browsers'].most_common(10):
        html += f'<tr><td>{escape(browser)}</td><td>{count:,}</td></tr>\n'
    html += "</table>\n</div>\n</div>\n"

    html += """
<div class="table-container">
<h3 style="margin-top:0">HTTP Status Codes</h3>
<table><tr><th>Status</th><th>Count</th></tr>
"""
    for status, count in sorted(stats['status_codes'].items()):
        html += f'<tr><td>{status}</td><td>{count:,}</td></tr>\n'
    html += "</table>\n</div>\n"

    html += f"""
<p class="generated">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>

<script>
const dailyLabels = {daily_labels};
const dailyRequests = {daily_requests};
const dailyUniques = {daily_uniques};
const dailyPages = {daily_pages};
const dailyBots = {daily_bots};
const weeklyLabels = {weekly_labels};
const weeklyRequests = {weekly_requests};
const weeklyUniques = {weekly_uniques};
const hourlyData = {hourly_data};

new Chart(document.getElementById('dailyChart'), {{
  type: 'line',
  data: {{
    labels: dailyLabels,
    datasets: [
      {{ label: 'Total Requests', data: dailyRequests, borderColor: '#4a90d9', fill: false, pointRadius: 0, borderWidth: 1.5 }},
      {{ label: 'Page Views', data: dailyPages, borderColor: '#50c878', fill: false, pointRadius: 0, borderWidth: 1.5 }},
      {{ label: 'Unique IPs', data: dailyUniques, borderColor: '#ff6b6b', fill: false, pointRadius: 0, borderWidth: 1.5 }},
    ]
  }},
  options: {{ responsive: true, interaction: {{ mode: 'index', intersect: false }}, scales: {{ x: {{ ticks: {{ maxTicksLimit: 15 }} }} }} }}
}});

new Chart(document.getElementById('weeklyChart'), {{
  type: 'bar',
  data: {{
    labels: weeklyLabels,
    datasets: [
      {{ label: 'Requests', data: weeklyRequests, backgroundColor: 'rgba(74,144,217,0.6)' }},
      {{ label: 'Unique IPs', data: weeklyUniques, backgroundColor: 'rgba(255,107,107,0.6)' }},
    ]
  }},
  options: {{ responsive: true, scales: {{ x: {{ ticks: {{ maxTicksLimit: 15 }} }} }} }}
}});

new Chart(document.getElementById('hourlyChart'), {{
  type: 'bar',
  data: {{
    labels: Array.from({{length:24}}, (_,i) => i + ':00'),
    datasets: [{{ label: 'Requests', data: hourlyData, backgroundColor: 'rgba(74,144,217,0.6)' }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
}});

new Chart(document.getElementById('botChart'), {{
  type: 'line',
  data: {{
    labels: dailyLabels,
    datasets: [
      {{ label: 'Human', data: dailyLabels.map((d,i) => dailyRequests[i] - dailyBots[i]), borderColor: '#50c878', fill: true, backgroundColor: 'rgba(80,200,120,0.15)', pointRadius: 0, borderWidth: 1.5 }},
      {{ label: 'Bot', data: dailyBots, borderColor: '#ff6b6b', fill: true, backgroundColor: 'rgba(255,107,107,0.15)', pointRadius: 0, borderWidth: 1.5 }},
    ]
  }},
  options: {{ responsive: true, interaction: {{ mode: 'index', intersect: false }}, scales: {{ x: {{ ticks: {{ maxTicksLimit: 10 }}, display: false }}, y: {{ stacked: true }} }} }}
}});
</script>
</body>
</html>
"""
    return html


def main():
    print("Loading logs...", flush=True)
    records = load_logs()
    print(f"Loaded {len(records):,} records", flush=True)

    print("Analyzing...", flush=True)
    stats = analyze(records)

    print("Generating HTML...", flush=True)
    html = generate_html(stats)

    output = Path("tgn_analytics.html")
    output.write_text(html)
    print(f"Report written to {output.resolve()}", flush=True)
    print(f"  Date range: {stats['first_date'].strftime('%Y-%m-%d')} to {stats['last_date'].strftime('%Y-%m-%d')}")
    print(f"  Total requests: {stats['total_requests']:,}")
    print(f"  Unique IPs: {len(stats['all_ips']):,} (human: {len(stats['human_ips']):,})")
    print(f"  Bot requests: {stats['bot_requests']:,} ({stats['bot_requests']/stats['total_requests']*100:.0f}%)")


if __name__ == '__main__':
    main()
