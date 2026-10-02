def success_line(ok, total):
    if total == 0:
        return "success: n/a"
    return "success: %.1f%%" % (100.0 * ok / total)


def error_line(bad, total):
    if total == 0:
        return "errors: n/a"
    return "errors: %.1f%%" % (100.0 * bad / total)


def coverage_line(covered, lines):
    if lines == 0:
        return "coverage: n/a"
    pct = 100.0 * covered / lines
    if pct > 99.9 and covered != lines:
        pct = 99.9                       # never show 100.0% unless it is complete
    return "coverage: %.1f%%" % pct
