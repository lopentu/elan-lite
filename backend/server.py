import argparse, json, os, pathlib, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from .core import Store, ValidationError, validate_pose
from .eaf import import_eaf, export_eaf


class Handler(BaseHTTPRequestHandler):
    store = None
    lock = threading.RLock()
    assets = pathlib.Path("dist")

    def response(self, status, data, ctype="application/json", headers=None):
        raw = (
            json.dumps(data, ensure_ascii=False).encode()
            if ctype == "application/json"
            else data if isinstance(data, bytes) else data.encode()
        )
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' blob: data:",
        )
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.valid_host():
            return self.response(403, {"error": "Loopback Host required"})
        with self.lock:
            try:
                path = urlparse(self.path).path
                if path == "/api/projects":
                    return self.response(
                        200, self.store.rows("SELECT id,name,duration FROM projects")
                    )
                if path.startswith("/api/project/"):
                    parts = path.split("/")
                    pid = parts[3]
                    if len(parts) > 4 and parts[4] == "eaf":
                        return self.response(
                            200, export_eaf(self.store, pid), "application/xml"
                        )
                    if len(parts) > 4 and parts[4] == "backup":
                        data = self.store.snapshot(pid)
                        data["source_eaf"] = self.store.rows(
                            "SELECT source_eaf FROM projects WHERE id=?", (pid,)
                        )[0]["source_eaf"]
                        return self.response(200, data)
                    return self.response(200, self.store.snapshot(pid))
                target = (self.assets / (path.lstrip("/") or "index.html")).resolve()
                if (
                    not target.is_relative_to(self.assets.resolve())
                    or not target.is_file()
                ):
                    return self.response(404, {"error": "Not found; run npm run build"})
                import mimetypes

                raw = target.read_bytes()
                ctype = (
                    mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                )
                requested = self.headers.get("Range")
                if requested:
                    import re

                    match = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
                    if not match:
                        return self.response(
                            416, b"", ctype, {"Content-Range": f"bytes */{len(raw)}"}
                        )
                    start = int(match[1])
                    end = min(int(match[2]) if match[2] else len(raw) - 1, len(raw) - 1)
                    if start > end:
                        return self.response(
                            416, b"", ctype, {"Content-Range": f"bytes */{len(raw)}"}
                        )
                    return self.response(
                        206,
                        raw[start : end + 1],
                        ctype,
                        {
                            "Accept-Ranges": "bytes",
                            "Content-Range": f"bytes {start}-{end}/{len(raw)}",
                        },
                    )
                return self.response(200, raw, ctype, {"Accept-Ranges": "bytes"})
            except ValidationError as e:
                return self.response(400, {"error": str(e)})

    def valid_host(self):
        return self.headers.get("Host", "").split(":")[0] in ("localhost", "127.0.0.1")

    def do_POST(self):
        if not self.valid_host():
            return self.response(403, {"error": "Loopback Host required"})
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self.response(403, {"error": "Cross-origin writes blocked"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.response(415, {"error": "JSON required"})
        with self.lock:
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size > 8_000_000:
                    raise ValidationError("Request too large")
                d = json.loads(self.rfile.read(size))
                path = urlparse(self.path).path
                pid = d.get("project_id")
                if path == "/api/create-project":
                    result = self.store.create_project(d["name"], d["duration"])
                elif path == "/api/annotation":
                    result = self.store.save_annotation(pid, d)
                elif path == "/api/delete":
                    if d["id"] not in [
                        a["id"] for a in self.store.snapshot(pid)["annotations"]
                    ]:
                        raise ValidationError("Unknown annotation")
                    self.store.db.execute(
                        "DELETE FROM annotations WHERE id=?", (d["id"],)
                    )
                    self.store.db.commit()
                    result = True
                elif path == "/api/lexicon":
                    result = self.store.lexicon(d)
                elif path == "/api/propose":
                    self.store.propose(pid)
                    result = True
                elif path == "/api/review":
                    self.store.review(pid, d["id"], d["decision"], d.get("edits"))
                    result = True
                elif path == "/api/overlap":
                    result = self.store.overlap(
                        pid, d["start"], d["end"], d.get("channels")
                    )
                elif path == "/api/import-eaf":
                    result = import_eaf(self.store, d["xml"])
                elif path == "/api/pose":
                    p = self.store.snapshot(pid)
                    validate_pose(d["pose"], p["duration"])
                    self.store.db.execute(
                        "UPDATE projects SET pose=? WHERE id=?",
                        (json.dumps(d["pose"]), pid),
                    )
                    self.store.db.commit()
                    result = True
                else:
                    return self.response(404, {"error": "Unknown endpoint"})
                return self.response(200, {"result": result})
            except (ValidationError, ValueError, KeyError, TypeError) as e:
                return self.response(400, {"error": str(e)})
            except Exception as e:
                import sqlite3

                if isinstance(e, sqlite3.IntegrityError):
                    return self.response(
                        400, {"error": "Database integrity constraint failed"}
                    )
                raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="data/elan-lite.sqlite")
    args = parser.parse_args()
    pathlib.Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    Handler.store = Store(args.db)
    Handler.store.demo()
    print(f"ELAN-lite local only: http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
