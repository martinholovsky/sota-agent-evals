import sys


def main(argv):
    try:
        nums = [float(x) for x in open(argv[1]).read().split()]
    except Exception as e:
        print("error:", e)
        return 0
    print(sum(nums))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
