# Run 1 — static analysis, same settings on both builds (2026-11-18)

Scope: each build's `docket/`, Dockerfile and workflows; tests excluded.

| tool | lib-1 (library) | bare-1 (no library) |
|---|---|---|
| ruff 0.16.2, `--isolated --select E,F,W,B,S,UP,SIM,BLE,PL,RUF,A,C4,DTZ,TRY,PERF,N` | 71 on 1,515 lines (47/kLOC), mostly TRY003/PLR2004 | 38 on 963 lines (39/kLOC); 2 blind `except Exception`, 1 `raise` without `from` |
| bandit 1.9.4 | 1 (B608, false positive: literal `where` fragments, values bound) | 1 (B608, false positive: migration names checked against a strict pattern) |
| opengrep 1.33.1, registry packs p/python, p/security-audit, p/owasp-top-ten, p/dockerfile, p/github-actions | 2 dependabot-missing-cooldown; 1 csv-writer-injection (false positive: neutralised, hidden test passes) | 3 github-actions-mutable-action-tag; 1 csv-writer-injection (same false positive) |
| opengrep, archived `opengrep/opengrep-rules` (fork of semgrep-rules, 2024-12-13; repo archived) | 9, of which 6 false positives (SQLAlchemy rules on sqlite3, Python 3.7 compat, WSGI file streaming) | 7; it flagged the unpinned base image but missed the mutable action tags |

No real security vulnerability from any tool in either build. The archived rule set is not a usable
source: it misses a real finding the current packs catch and adds false ones. Opengrep's own skill
points at the registry packs (`--config p/...`).

**Note 2026-11-18 (session close):** `dependabot-missing-cooldown` overstates lib-1's config: GitHub's Dependabot
options reference (read 2026-11-18) applies a 3-day cooldown to version updates when none is configured.
lib-1 had 3 days, not none; the library recommends 5.
