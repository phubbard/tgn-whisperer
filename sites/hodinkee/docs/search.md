# Search

<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<script src="/pagefind/pagefind-ui.js"></script>
<div id="search"></div>
<script>
    window.addEventListener('DOMContentLoaded', (event) => {
        new PagefindUI({ element: "#search", showSubResults: true });
    });
</script>

## About Search

This search engine is powered by [Pagefind](https://pagefind.app/), a fully static search library that runs entirely in your browser - no server required!

It indexes all episodes and transcripts, allowing you to search across the entire Hodinkee Radio archive.

### Tips

- Search is case-insensitive
- Use quotes for exact phrases: `"perpetual calendar"`
- Multiple words search for all terms: `patek philippe`
- Results show relevant excerpts from episodes
