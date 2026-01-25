# Search

<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<div id="search"></div>
<script src="/pagefind/pagefind-ui.js"></script>
<script>
    (function initPagefind() {
        if (typeof PagefindUI !== 'undefined') {
            new PagefindUI({ element: "#search", showSubResults: true });
        } else {
            setTimeout(initPagefind, 50);
        }
    })();
</script>

## About Search

This search engine is powered by [Pagefind](https://pagefind.app/), a fully static search library that runs entirely in your browser - no server required!

It indexes all episodes, transcripts, and show notes, allowing you to search across the entire 40 and 20 archive.

### Tips

- Search is case-insensitive
- Use quotes for exact phrases: `"vintage watch"`
- Multiple words search for all terms: `rolex gmt`
- Results show relevant excerpts from episodes
