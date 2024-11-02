# {Podcast Name} Extraction Requirements

## Podcast Information 
- Name: {full name}
- ID: {short identifier}
- Base URLs:
  - Episode List: {url}
  - Episode Details: {url pattern}
  - Show Notes: {url pattern if applicable}
- Initial Analysis Date: {date}

## Extraction Requirements
1. Episode List
   - Required metadata fields
   - Ordering/numbering patterns
   - Date format specifications
   - Special episode handling

2. Episode Details
   - Required content sections
   - Special formatting requirements
   - Media handling requirements
   - Cross-reference requirements

3. Output Format Requirements
   - File naming convention
   - Content structure template
   - Required sections
   - Formatting rules

## Implementation Details

### Episode List Page HTML Patterns
```html
<!-- Example episode list HTML structure -->
```

### Episode Detail Page HTML Patterns
```html
<!-- Example episode detail HTML structure -->
```

### Show Notes Page HTML Patterns (if applicable)
```html
<!-- Example show notes HTML structure -->
```

### Navigation Pattern
```python
# Pseudocode for content extraction flow
```

### Error Handling Requirements
1. Missing Pages
   - Logging requirements
   - Fallback behavior
   - Recovery steps

2. Malformed Content
   - Validation steps
   - Partial content handling
   - Quality checks

3. Rate Limiting
   - Request timing
   - robots.txt compliance
   - Backoff strategy

4. Network Issues
   - Retry strategy
   - Progress preservation
   - Failure documentation

## Known Edge Cases
- Special episode patterns
- Content variations
- Access restrictions
- Character encoding issues
- Media handling edge cases
- Authentication requirements

## Example Output
```markdown
# Example of expected output format
```

## Analysis History

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