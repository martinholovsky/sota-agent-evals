#!/usr/bin/env python3
"""Draw cases-v5's screening order from OWASP ASVS 5.0.0 ids (SELECTION.md, "Sampling").

Reads ids only, never requirement text (ASVS is CC BY-SA; this repository is Apache-2.0).

  python3 cases-v5/tools/sample.py PATH/TO/ASVS/5.0/en > cases-v5/ORDER.txt

Fails closed unless exactly 345 ids are found, the count SELECTION.md pins.
"""
import hashlib
import pathlib
import random
import re
import sys

SEED = "cases-v5: OWASP ASVS 5.0.0 sample, frozen 2026-10-13"
EXPECTED = 345
ROW = re.compile(r"^\| \*\*(\d+)\.(\d+)\.(\d+)\*\* \|", re.M)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(sys.argv[1])
    files = sorted(src.glob("0x*-V*.md"))
    ids = sorted({tuple(int(x) for x in m.groups())
                  for f in files for m in ROW.finditer(f.read_text(encoding="utf-8"))})
    if len(ids) != EXPECTED:
        raise SystemExit("found %d ids in %d files under %s, expected %d" % (len(ids), len(files), src, EXPECTED))
    order = ["V%d.%d.%d" % t for t in ids]
    random.Random(int(hashlib.sha256(SEED.encode()).hexdigest(), 16)).shuffle(order)
    sys.stdout.write("\n".join(order) + "\n")
    print("sampled order of %d ids from %d files" % (len(order), len(files)), file=sys.stderr)


if __name__ == "__main__":
    main()
