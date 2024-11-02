# WCL (Watch Collector's League) Podcast Extraction Guide

## Podcast Information
- Name: WCL (Watch Collector's League)  
- ID: wcl
- Base URLs:
  - Episode List: https://wcl.phfactor.net/episodes/
  - Episode Details: https://wcl.phfactor.net/{episode_number}.0/episode/
  - Show Notes: https://the40and20podcast.podbean.com/e/{episode-slug}/
- Initial Analysis Date: 2024-02-01

## Extraction Requirements

1. Episode List
   - Episode title
   - Episode number 
   - Publication date
   - Episode description
   - Links to episode detail pages

2. Episode Details
   - Full transcript
   - Links section
   - Synopsis
   - Publication timestamp
   - Download counts (from Podbean)

3. Output Format Requirements
   - File naming: episode_{number}.md
   - Content structure:
     ```markdown
     # Episode {number} - {title}
     Published: {date}
     
     ## Synopsis
     {synopsis}
     
     ## Links
     {links}
     
     ## Transcript
     {transcript}
     ```

## Technical Implementation Details

### Collection Commands
```bash
# Create cache directory structure
mkdir -p wcl_cache/{episodes,episode_pages,podbean}

# Get the main episode list 
curl -A "Mozilla/5.0" \
     -o "./wcl_cache/episodes/index.html" \
     "https://wcl.phfactor.net/episodes/"

# Get sample episode pages across different time periods
for num in 1 2 50 91 150 200; do
  curl -A "Mozilla/5.0" \
       -o "./wcl_cache/episode_pages/episode_${num}.html" \
       "https://wcl.phfactor.net/${num}.0/episode/"
done

# Get corresponding Podbean pages 
curl -A "Mozilla/5.0" \
     -o "./wcl_cache/podbean/episode_1.html" \
     "https://the40and20podcast.podbean.com/e/episode-1-the-inaugural-episode-1595962788/"
```

### Content Encoding & Processing
1. Character Encoding
   - Pages use UTF-8 encoding
   - Special characters like curly quotes and em-dashes need proper handling
   - HTML entities in transcripts need decoding

2. Transcript Format
   - Speaker tags wrapped in italics/emphasis: `*Speaker*`
   - Multiple line breaks between speaker segments
   - Speaker names should be column headers

3. HTML Patterns
```html
<!-- Episode list page -->
.episode-list-type-list .row .row-cols-1 contains episodes
  .card-title .e-title contains episode title
  .episode-description contains synopsis

<!-- Episode detail page -->
.navbar-expand-md .bs-sidebar .hidden-print contains TOC
.col-md-9[role="main"] contains main content
  h1 contains episode title
  div[Published on] contains date
  h2[Synopsis] contains synopsis
  h2[Links] contains links
  h2[Transcript] contains transcript
    td contains speaker name
    td contains speaker text

<!-- Podbean page -->
.episode-description contains clean synopsis
.download-episodes contains download count
```

### Content Cleaning
1. Text Processing
   ```python
   def clean_transcript(text):
       """Clean up transcript text with podcast-specific handling"""
       # Remove boilerplate
       text = re.sub(r'Documentation built with.*', '', text)
       
       # Fix speaker tags
       text = re.sub(r'\*([^*]+)\*\s+', r'\1: ', text)
       
       # Normalize whitespace while preserving paragraphs
       text = re.sub(r'\n{3,}', '\n\n', text)
       
       return text.strip()

   def parse_date(date_str):
       """Handle podcast's specific date formats"""
       # Example: "Wed, 31 Oct 2018 12:00:00 -0700"
       return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
   ```

2. General Cleanup Rules
   - Remove navigation elements
   - Strip excess whitespace but preserve paragraph breaks
   - Normalize inconsistent date formats
   - Handle special cases where transcript format varies
   - Remove boilerplate footer/header content
   - Clean up any HTML artifacts in plaintext sections

### Error Handling
1. Missing Pages:
   - Log error
   - Continue processing other episodes
   - Mark episode as incomplete

2. Malformed Content:
   - Basic HTML sanitization
   - Extract text content only if formatting fails
   - Log warnings

3. Rate Limiting:
   - 2 second delay between requests
   - Respect robots.txt
   - User agent rotation if needed
   - Implement exponential backoff for failures
   - Use If-Modified-Since headers
   - Cache fetched pages locally

## Example Output
```markdown
# Episode 91 - WatchClicker Potpourri with Will
Published: Wed, 22 Jul 2020 22:20:00 -0700

## Synopsis
In this 91st Episode of 40 and 20, we catch up with WatchClicker's Editor in Chief, Will...

## Links
- Episode page: https://the40and20podcast.podbean.com/e/episode-91-watchclicker-potpourri-with-will/
- MP3: https://mcdn.podbean.com/mf/web/ca5ch8/stream_862901941-40and20-episode-19-watchclicker-potpourri-with-will.mp3

## Transcript
Andrew: Hello, fellow watch lovers...
[Rest of transcript]
```
