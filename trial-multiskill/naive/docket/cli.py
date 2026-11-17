import argparse
import sys

from . import admin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("migrate")
    t = sub.add_parser("create-tenant")
    t.add_argument("name")
    u = sub.add_parser("create-user")
    u.add_argument("tenant")
    u.add_argument("username")
    u.add_argument("--admin", action="store_true")
    args = parser.parse_args()
    if args.command == "migrate":
        admin.migrate(args.db)
    elif args.command == "create-tenant":
        admin.create_tenant(args.db, args.name)
    elif args.command == "create-user":
        password = sys.stdin.readline().strip()
        admin.create_user(args.db, args.tenant, args.username, password, admin=args.admin)
    print("done")


if __name__ == "__main__":
    main()
