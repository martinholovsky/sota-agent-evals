def fmt_pct(part, whole):
    if whole == 0:
        return "n/a"
    pct = 100.0 * part / whole
    if pct > 99.9 and part != whole:
        pct = 99.9
    return "%.1f%%" % pct


def success_line(ok, total):
    return "success: " + fmt_pct(ok, total)


def error_line(bad, total):
    return "errors: " + fmt_pct(bad, total)


def coverage_line(covered, lines):
    return "coverage: " + fmt_pct(covered, lines)
