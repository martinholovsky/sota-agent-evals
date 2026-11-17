import io
import json
import os
import tempfile
import unittest

from docket import admin
from docket.app import create_app


def call(app, method, path, body=b"", token=None, query=""):
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
               "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
    if token:
        environ["HTTP_AUTHORIZATION"] = "Bearer " + token
    out = {}

    def start_response(status, headers):
        out["status"] = int(status.split()[0])
    out["body"] = b"".join(app(environ, start_response))
    return out


class BasicTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "test.db")
        admin.create_tenant(self.db, "acme")
        admin.create_user(self.db, "acme", "alice", "secret", admin=True)
        self.app = create_app(self.db, http_post=lambda u, b, h: 200, resolve=lambda h: ["1.2.3.4"])

    def login(self):
        r = call(self.app, "POST", "/login", json.dumps({"tenant": "acme", "username": "alice",
                                                         "password": "secret"}).encode())
        return json.loads(r["body"])["token"]

    def test_login(self):
        self.assertTrue(self.login())

    def test_upload_and_download(self):
        token = self.login()
        r = call(self.app, "POST", "/documents", b"hello", token, "filename=a.txt")
        self.assertEqual(r["status"], 201)
        doc_id = json.loads(r["body"])["id"]
        r = call(self.app, "GET", "/documents/" + doc_id, token=token)
        self.assertEqual(r["body"], b"hello")

    def test_export(self):
        token = self.login()
        call(self.app, "POST", "/documents", b"hello", token, "filename=a.txt")
        r = call(self.app, "GET", "/tenant/export.csv", token=token)
        self.assertIn(b"a.txt", r["body"])


if __name__ == "__main__":
    unittest.main()
