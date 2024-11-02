# Podcast Scraper Documentation Structure

## Document Naming Convention
`{podcast-id}-extraction-requirements.md`

Examples:
- `tgn-extraction-requirements.md`
- `wcl-extraction-requirements.md`

## Required Document Sections

### 1. Overview
```markdown
# {Podcast Name} Extraction Requirements

## Podcast Information
- Name: {full name}
- ID: {short identifier}
- Base URL: {url}
- Initial Analysis Date: {date}
```

### 2. Requirements
```markdown
## Extraction Requirements
- Output format requirements
- Required metadata
- Special handling rules
- Error conditions to handle
```

### 3. Implementation Specification
```markdown
## Implementation Details
- HTML selectors
- Text processing rules
- Link extraction patterns
```

### 4. Analysis History
```markdown
## Page Analysis History

### Episode List Pages
- Date: {date}
- URL: {url}
- Key findings:
  - {finding 1}
  - {finding 2}

### Episode Detail Pages
1. {episode-id}
   - Date analyzed: {date}
   - URL chain:
     - {intermediate url}
     - {final url}
   - Special cases discovered:
     - {case 1}
     - {case 2}

2. {episode-id}
   [...]
```

### 5. Edge Cases
```markdown
## Known Edge Cases
- Case: {description}
  - Example URL: {url}
  - Date discovered: {date}
  - Handling strategy: {strategy}
```