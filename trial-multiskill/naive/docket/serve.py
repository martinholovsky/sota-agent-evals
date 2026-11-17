import argparse
from wsgiref.simple_server import make_server

from .app import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    app = create_app(args.db)
    app.start_worker()
    print(f"Serving on port {args.port}")
    make_server("0.0.0.0", args.port, app).serve_forever()


if __name__ == "__main__":
    main()
