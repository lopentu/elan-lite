import unittest, tempfile, threading, json, http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
from backend.server import Handler
from backend.core import Store


class LocalHTTP(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(":memory:")
        self.pid = self.store.demo()
        Path(self.tmp.name, "video.mp4").write_bytes(b"0123456789")

        class TestHandler(Handler):
            def log_message(self, *args):
                pass

        TestHandler.store = self.store
        TestHandler.assets = Path(self.tmp.name)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.store.db.close()
        self.tmp.cleanup()

    def request(self, path, method="GET", data=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request(
            method, path, body=json.dumps(data) if data else None, headers=headers or {}
        )
        r = c.getresponse()
        result = (r.status, dict(r.getheaders()), r.read())
        c.close()
        return result

    def test_ranges_and_local_host_security(self):
        status, headers, raw = self.request(
            "/video.mp4", headers={"Range": "bytes=3-6"}
        )
        self.assertEqual(status, 206)
        self.assertEqual(raw, b"3456")
        self.assertEqual(headers["Content-Range"], "bytes 3-6/10")
        self.assertEqual(
            self.request("/video.mp4", headers={"Range": "bytes=100-200"})[0], 416
        )
        self.assertEqual(
            self.request("/api/projects", headers={"Host": "evil.example"})[0], 403
        )
        self.assertEqual(
            self.request(
                "/api/propose",
                "POST",
                {"project_id": self.pid},
                {"Content-Type": "application/json", "Origin": "https://evil.example"},
            )[0],
            403,
        )
        self.assertEqual(
            self.request(
                "/api/propose",
                "POST",
                {"project_id": self.pid},
                {"Content-Type": "text/plain"},
            )[0],
            415,
        )

    def test_annotation_http_persistence(self):
        a = self.store.snapshot(self.pid)["annotations"][0]
        a.update(project_id=self.pid, value="HTTP persisted")
        self.assertEqual(
            self.request(
                "/api/annotation", "POST", a, {"Content-Type": "application/json"}
            )[0],
            200,
        )
        status, _, raw = self.request("/api/project/" + self.pid)
        self.assertEqual(status, 200)
        self.assertTrue(
            any(a["value"] == "HTTP persisted" for a in json.loads(raw)["annotations"])
        )
