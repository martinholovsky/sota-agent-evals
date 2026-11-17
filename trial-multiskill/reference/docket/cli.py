"""Admin CLI: python -m docket.cli --db PATH <command>.

Exit status: 0 success, 1 operation failed (message on stderr), 2 usage error
(argparse). Results go to stdout, diagnostics to stderr."""
import argparse
import sqlite3
import sys

from . import admin, db


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m docket.cli", description="Docket administration")
    parser.add_argument("--db", required=True, help="path to the SQLite database file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply pending migrations")
    tenant = sub.add_parser("create-tenant", help="create a tenant")
    tenant.add_argument("name")
    user = sub.add_parser("create-user", help="create a user; password is read from the first line of stdin")
    user.add_argument("tenant")
    user.add_argument("username")
    user.add_argument("--admin", action="store_true", help="make the user a tenant admin")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "migrate":
            applied = admin.migrate(args.db)
            print(f"applied {len(applied)} migration(s)" + (": " + ", ".join(applied) if applied else ""))
        elif args.command == "create-tenant":
            admin.create_tenant(args.db, args.name)
            print(f"created tenant {args.name}")
        elif args.command == "create-user":
            line = sys.stdin.readline()
            password = line.rstrip("\r\n")
            if not password:
                print("error: no password on stdin", file=sys.stderr)
                return 1
            admin.create_user(args.db, args.tenant, args.username, password, admin=args.admin)
            print(f"created user {args.username} in tenant {args.tenant}"
                  + (" (admin)" if args.admin else ""))
    except (admin.AdminError, db.MigrationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"error: database error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
