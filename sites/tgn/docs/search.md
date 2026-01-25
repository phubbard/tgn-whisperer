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

It indexes all episodes, transcripts, and show notes, allowing you to search across the entire TGN archive.

### Tips

- Search is case-insensitive
- Use quotes for exact phrases: `"dive watch"`
- Multiple words search for all terms: `seiko chronograph`
- Results show relevant excerpts from episodes
