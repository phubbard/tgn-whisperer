# Multi-Podcast Content Extraction System

## System Overview
A scheduled content extraction system that handles multiple podcast sources, each with unique scraping patterns, while maintaining a consistent output format and error handling approach.

## Podcast Source Specifications

### The Grey NATO (TGN)
1. Episode List Source:
   - Base URL: https://tgn.phfactor.net/episodes/
   - Pattern: Episodes listed with numeric identifiers

2. Navigation Pattern:
   - First-level link pattern: https://tgn.phfactor.net/{episode_number}.0/episode/
   - Second-level link pattern: https://thegreynato.substack.com/p/{episode-slug}

3. Content Pattern:
   - Text format: "{timestamp} {description}"
   - Example: "2:50 Doxa sub 200T"
   - Links follow text entries
   - Timestamp range: typically 2:XX to 56:XX format

### Watch Collector's League (WCL)
1. Episode List Source:
   - Base URL: https://wcl.phfactor.net/episodes/
   - Pattern: Episodes with titles and timestamps

2. Navigation Pattern:
   - First-level link: https://wcl.phfactor.net/{episode_number}.0/episode/
   - Second-level link: https://the40and20podcast.podbean.com/e/{episode-slug}

3. Content Pattern:
   - Text format varies
   - Example link text: "Aqua Terra Moonshine Gold"
   - Links to watch-related content

## Core Requirements

### Configuration Management
1. Per-podcast configuration:
   - Base URL
   - Navigation patterns
   - Content extraction rules
   - Timestamp handling rules
2. Extensible design:
   - Easy addition of new podcast sources
   - Plugin-style content extractors

### Data Collection
1. Primary scraping:
   - Configure per-podcast episode list extraction
   - Handle different URL patterns
   - Extract episode metadata

2. Secondary scraping:
   - Support multi-level navigation (2 levels for current examples)
   - Handle different content page formats
   - Extract links and descriptions based on podcast-specific patterns

### Content Formatting
1. Output structure:
   - One markdown file per episode
   - Consistent format across all podcasts:
     ```markdown
     - {description} [{url}]
     ```
   - Timestamps removed from final output
   - Links preserved with original URLs

### Storage & Organization
1. Filesystem structure:
   ```
   /content
     /{podcast_id}
       /episodes
         /{episode_id}.md
       /status.json
   ```
2. Status tracking:
   - Per-podcast status files
   - Global system status

### Error Handling & Reporting
1. Process monitoring:
   - Track per-podcast processing status
   - Handle podcast-specific error cases
   - Aggregate errors across all podcasts

### Orchestration
1. Prefect workflow:
   - Single flow managing multiple podcasts
   - Parallel processing across podcasts
   - Sequential processing within each podcast

### Technical Components
1. Primary technologies:
   - Python with podcast-specific extractors
   - Prefect for workflow management
   - Requests for HTTP operations
   - Custom parsing logic per podcast

## Processing Flow
1. Daily trigger
2. For each configured podcast:
   - Fetch episode list
   - Parse using podcast-specific rules
   - For each unprocessed episode:
     - Navigate through intermediate pages
     - Extract content using podcast-specific patterns
     - Format to standard markdown
     - Save to appropriate location
3. Generate combined report
4. Update status files

## Example Processing Cases

### TGN Episode Processing
```
Input: "56:51 "Turn This Ship Around" (book, L. David Marquet)"
Link: https://davidmarquet.com/turn-the-ship-around-book/
Output: - Turn This Ship Around (book, L. David Marquet) [https://davidmarquet.com/turn-the-ship-around-book/]
```

### WCL Episode Processing
```
Input: "Aqua Terra Moonshine Gold"
Link: https://monochrome-watches.com/omega-seamaster-aqua-terra-collection-moonshine-gold-2024-new-references-41mm-38mm-introducing-price/
Output: - Aqua Terra Moonshine Gold [https://monochrome-watches.com/omega-seamaster-aqua-terra-collection-moonshine-gold-2024-new-references-41mm-38mm-introducing-price/]
```
