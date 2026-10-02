def wrap(text: str, width: int) -> str:
    """Greedy word wrap.
    - Paragraphs are separated by one or more blank lines; output separates paragraphs
      with exactly one blank line ("\n\n").
    - Within a paragraph, words are separated by any whitespace (including newlines) and
      are re-joined with single spaces, greedily filling lines up to `width` characters.
    - A word longer than width is split into chunks of exactly width (the last may be
      shorter), each on its own line.
    - No line has trailing spaces; the result has no leading/trailing blank lines.
    - width < 1 raises ValueError."""
    raise NotImplementedError
