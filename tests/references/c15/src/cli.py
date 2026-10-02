import sys


def main(argv):
    if len(argv) != 2:
        print("usage: cli.py FILE", file=sys.stderr)
        return 2
    try:
        with open(argv[1]) as f:
            nums = [float(x) for x in f.read().split()]
    except (OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    print(sum(nums))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
