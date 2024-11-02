# The Grey NATO Extraction Requirements

## Podcast Information
- Name: The Grey NATO
- ID: tgn
- Base URLs: 
  - Episode List: https://tgn.phfactor.net/episodes/
  - Episode Details: https://tgn.phfactor.net/{episode_number}.0/episode/
  - Show Notes: https://thegreynato.substack.com/p/{episode-slug}
- Initial Analysis Date: 2024-02-11

## Extraction Requirements
1. Episode List
   - Must extract episode number, title, and publication date
   - Episodes are listed in reverse chronological order
   - Episode numbers in format NNN.0 (e.g. 292.0)
   - Some episodes may have .5 numbers for special episodes
   - Publication dates in RFC 2822 format

2. Episode Details
   - Must preserve complete synopsis section
   - Must extract all links mentioned in transcript
   - Must preserve complete transcript if available
   - Must preserve show notes section with timestamps and links

3. Output Format Requirements
   - One markdown file per episode
   - Standard structure:
     ```markdown 
     # Title
     
     Published on {date}
     
     ## Synopsis
     {synopsis text}
     
     ## Links
     {all extracted links}
     
     ## Transcript
     {full transcript if available}
     ```

## Implementation Details

### Episode List Page HTML Patterns
```html
<div class="bs-sidebar">
  <!-- Each episode -->
  <a href="/292.0/episode/">The Grey NATO -- 292 -- Drafting Summer Watches (And A New UDT!)</a>
  Thu, 11 Jul 2024 06:00:00 -0400
</div>
```

### Episode Detail Page HTML Patterns 
```html
<div class="col-md-9" role="main">
  <h1>The Grey NATO -- 292 -- Drafting Summer Watches...</h1>
  
  <h2>Synopsis</h2>
  <p>Synopsis text...</p>

  <h2>Links</h2>
  <ul>
    <li><a href="...">Link text</a></li>
  </ul>

  <h2>Transcript</h2>
  <p>
    <strong>Speaker:</strong> Transcript text...
  </p>
</div>
```

### Show Notes Page HTML Patterns
```html
<div class="available-content">
  <!-- Show notes content -->
  <div class="body markup">
    <p>Show notes text and links...</p>
  </div>
</div>
```

### Navigation Pattern
1. Start at episode list page
2. For each episode:
   ```python
   episodes = soup.select(".bs-sidebar a[href*='/episode/']")
   for ep in episodes:
       num = extract_episode_num(ep['href'])  # Get NNN.0 format
       date = parse_date(ep.next_sibling)     # Parse RFC 2822
       title = ep.text
       
       # Get episode detail page
       detail_url = f"https://tgn.phfactor.net/{num}/episode/"
       detail_page = requests.get(detail_url)
       
       # Extract content sections
       synopsis = extract_synopsis(detail_page)
       links = extract_links(detail_page)
       transcript = extract_transcript(detail_page)
       
       # Get show notes if available
       if show_notes_url := find_show_notes_link(detail_page):
           notes = extract_show_notes(show_notes_url)
           
       # Save markdown file
       save_markdown(num, title, date, synopsis, links, transcript, notes)
   ```

### Error Handling Requirements
1. Missing Pages
   - Log error if episode detail page 404s
   - Continue to next episode
   - Note missing content in output file

2. Malformed Content
   - Log warning if required sections missing
   - Preserve partial content
   - Note incomplete sections in output

3. Rate Limiting
   - Implement 1 second delay between requests
   - Respect site robots.txt
   - Handle 429 Too Many Requests with exponential backoff

4. Network Issues
   - Retry failed requests up to 3 times
   - Log permanent failures
   - Save partial progress

## Known Edge Cases
- Episode numbers may contain decimals for special episodes
- Some episodes lack transcripts
- Links section may contain relative URLs needing conversion to absolute
- Speaker attribution format in transcripts varies
- Special characters in titles need escaping in filenames
- Some show notes pages may be behind paywall
- Image content should be noted but not downloaded

## Example Output
```markdown
# The Grey NATO -- 292 -- Drafting Summer Watches (And A New UDT!)

Published on Thu, 11 Jul 2024 06:00:00 -0400

## Synopsis
This podcast episode discusses summer watches. The hosts draft different watch recommendations for various summer scenarios...

## Links
- [episode page](https://thegreynato.substack.com/p/292-summer-draft)
- [episode MP3](https://www.buzzsprout.com/2049759/15388589...)

## Transcript
Henry Catchpole: Hello and welcome to a hijacking of the grey NATO...
```