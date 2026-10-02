def allocate(total_cents: int, ratios: list) -> list:
    """Split total_cents across len(ratios) parts proportionally to ratios.
    - Results are ints and ALWAYS sum exactly to total_cents.
    - Use largest remainder: give each part floor(total*r/sum), then hand the leftover
      cents one at a time to the parts with the largest fractional remainders; ties go to
      the EARLIER part.
    - total_cents may be negative: allocate abs(total) and negate every part.
    - ratios must be non-negative numbers with a positive sum, else ValueError; an empty
      ratios list is a ValueError."""
    raise NotImplementedError
