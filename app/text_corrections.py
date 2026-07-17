"""
Transcription vocabulary corrections.

Fluid Audio (STT) consistently mis-transcribes some show-specific vocabulary —
most notably the show name "The Grey NATO" (rendered as "Graynado", "Grey Nado",
etc.) and "Hodinkee" ("Hodinky", "Hodinki", ...), plus a handful of watch brands.

`normalize_transcript_text()` applies a curated set of regex substitutions to
transcript text at markdown-generation time. The raw STT output in
`whisper-output.json` is left untouched (it remains the authentic source); only
the displayed/searched transcript is corrected.

Design rules for every correction:
- URL-SAFE: only match tokens that never appear in a real URL. The show's real
  domains spell it "greynato"/"thegreynato.com" (with "nato"), so we correct only
  the "nado" family and never touch the "nato" spelled forms. Hodinkee's real
  domain is "hodinkee.com"; we correct only the mis-spelled forms, never
  "hodinkee" itself.
- UNAMBIGUOUS: we deliberately do NOT rewrite "gray NATO" (spaced), which can
  legitimately mean a grey NATO *strap* — the object the show is named after.
- Brand names are proper nouns, so the canonical capitalized form is always
  correct regardless of the matched text's case.

To add a term: append a (compiled_regex, replacement) tuple. Order matters where
patterns overlap (more specific first — e.g. "blancpans" before "blancpan").
"""
import re

# Each entry: (compiled pattern, replacement). Applied in order.
_CORRECTIONS = [
    # --- The Grey NATO (show name) — "nado" family only (never a URL) ---
    (re.compile(r"\bgr[ae]y[ \-]?nado\b", re.IGNORECASE), "Grey NATO"),

    # --- Hodinkee — misspelled forms only (real domain "hodinkee" untouched) ---
    (re.compile(r"\bhodink(?:y|i|e|ey|ie|a)\b", re.IGNORECASE), "Hodinkee"),
    (re.compile(r"\bhodingk?[iy]?\b", re.IGNORECASE), "Hodinkee"),

    # --- Watch brands (curated, high-confidence STT errors) ---
    (re.compile(r"\bblancpans\b", re.IGNORECASE), "Blancpains"),
    (re.compile(r"\bblancpan\b", re.IGNORECASE), "Blancpain"),
    (re.compile(r"\bblancpon\b", re.IGNORECASE), "Blancpain"),
    (re.compile(r"\bblompa\b", re.IGNORECASE), "Blancpain"),
    (re.compile(r"\baqua star\b", re.IGNORECASE), "Aquastar"),
    (re.compile(r"\bpelegos\b", re.IGNORECASE), "Pelagos"),
    (re.compile(r"\bvasheron\b", re.IGNORECASE), "Vacheron"),
    (re.compile(r"\bodemars?\b", re.IGNORECASE), "Audemars"),
    (re.compile(r"\btuder\b", re.IGNORECASE), "Tudor"),
    (re.compile(r"\bspeed master\b", re.IGNORECASE), "Speedmaster"),
    (re.compile(r"\bcerica\b", re.IGNORECASE), "Serica"),
    (re.compile(r"\blongine\b", re.IGNORECASE), "Longines"),
]


def normalize_transcript_text(text: str) -> str:
    """Apply curated transcription-vocabulary corrections to a string."""
    if not text:
        return text
    for pattern, replacement in _CORRECTIONS:
        text = pattern.sub(replacement, text)
    return text
