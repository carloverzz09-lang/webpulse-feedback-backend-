"""WebPulse feedback dashboard/API - Supabase + Resend, Python standard library.

Set all secrets in Render env vars. This app deliberately rejects feedback unless
persistent storage is configured, to avoid silently losing submissions.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import hmac
import io
import json
import logging
import os
from pathlib import Path
import base64
import zlib
import secrets
import threading
import time
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent

ASSETS = {
    'index.html': zlib.decompress(base64.b64decode('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')),
    'admin.css': zlib.decompress(base64.b64decode('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')),
    'admin.js': zlib.decompress(base64.b64decode('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')),
}

STATUSES = {"pending", "in_progress", "resolved"}
CATEGORIES = {"Incorrect finding", "Confusing screen", "Feature idea", "Other"}
SESSIONS: dict[str, dict] = {}
HITS: dict[tuple, deque] = defaultdict(deque)
LOCK = threading.Lock()
SESSION_TTL = 12 * 3600


def env(name: str) -> str:
    return os.getenv(name, "").strip()


def configured() -> bool:
    url = env("SUPABASE_URL")
    return url.startswith("https://") and bool(env("SUPABASE_SERVICE_ROLE_KEY"))


def allowed_origins() -> set[str]:
    return set(filter(None, [s.strip().rstrip("/") for s in
                            os.getenv("WEBPULSE_ALLOWED_ORIGINS", "https://webpulse-paras.carloverzz09.chatgpt.site").split(",")]))


def limited(kind, ip, maximum, seconds):
    key = (kind, ip)
    now = time.monotonic()
    with LOCK:
        window = HITS[key]
        while window and now - window[0] > seconds:
            window.popleft()
        if len(window) >= maximum:
            return True
        window.append(now)
        if len(HITS) > 12000:
            for k in list(HITS)[:2500]:
                if not HITS[k] or now - HITS[k][-1] > seconds:
                    HITS.pop(k, None)
    return False


def supabase(method, query=None, payload=None, prefer=None):
    """Send API call using server-only service role key. Never expose it to browser."""
    if not configured():
        raise RuntimeError("Persistent storage is not configured")
    full_url = env("SUPABASE_URL") + "/rest/v1/webpulse_feedback"
    if query:
        full_url += "?" + urlencode(query)
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "apikey": env("SUPABASE_SERVICE_ROLE_KEY"),
        "Authorization": "Bearer " + env("SUPABASE_SERVICE_ROLE_KEY"),
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    req = Request(full_url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=12) as response:
        raw = response.read(3 * 1024 * 1024)
        result = json.loads(raw) if raw else []
        return result


def admin_users(search_term, offset, profiles_only):
    if not configured():
        raise RuntimeError("Account storage is not configured")
    request = Request(env("SUPABASE_URL") + "/rest/v1/rpc/webpulse_admin_directory",
        data=json.dumps({"search_term": search_term, "page_offset": offset, "profiles_only": profiles_only}).encode(),
        headers={"apikey": env("SUPABASE_SERVICE_ROLE_KEY"),
                 "Authorization": "Bearer " + env("SUPABASE_SERVICE_ROLE_KEY"),
                 "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
    with urlopen(request, timeout=12) as response:
        result = json.loads(response.read(512 * 1024))
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        raise RuntimeError("Account directory did not return a valid page")
    return result


def all_rows():
    return supabase("GET", {"select": "*", "order": "id.desc", "limit": "1000"})


def notify(record):
    if not all([env("RESEND_API_KEY"), env("RESEND_FROM"), env("WEBPULSE_NOTIFY_EMAIL")]):
        return
    def task():
        try:
            data = json.dumps({
                "from": env("RESEND_FROM"),
                "to": [env("WEBPULSE_NOTIFY_EMAIL")],
                "subject": "WebPulse · New feedback #" + str(record["id"]),
                "text": "New feedback saved in your WebPulse dashboard.\n"
                        "Source: " + record["source"] + "\n"
                        "Category: " + record["category"] + "\n"
                        "For privacy, sign in to the admin dashboard to read the message.",
            }).encode("utf-8")
            req = Request("https://api.resend.com/emails", data=data, method="POST",
                          headers={"Authorization": "Bearer " + env("RESEND_API_KEY"),
                                   "Content-Type": "application/json"})
            with urlopen(req, timeout=12) as response:
                response.read()
        except Exception:
            logging.exception("Feedback stored but email notification failed")
    threading.Thread(target=task, daemon=True).start()


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Handler(BaseHTTPRequestHandler):
    server_version = "WebPulse/Feedback"
    sys_version = ""

    def log_message(self, fmt, *args):
        logging.info("%s %s", self.client_address[0], fmt % args)

    def path_only(self):
        return urlsplit(self.path).path

    def origin(self):
        return self.headers.get("Origin", "")

    def origin_ok(self):
        value = self.origin()
        return not value or value in allowed_origins() or value == "https://" + self.headers.get("Host", "")

    def common_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        if self.path_only() == "/api/feedback" and self.origin() in allowed_origins():
            self.send_header("Access-Control-Allow-Origin", self.origin())
            self.send_header("Vary", "Origin")

    def send(self, status=200, payload=None, body=None, mime="application/json; charset=utf-8", headers=()):
        data = body if body is not None else json.dumps(payload if payload is not None else {}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.common_headers()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def read_json(self, max_bytes=8192):
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise ValueError("Expected JSON")
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= max_bytes:
            raise ValueError("Invalid request size")
        value = json.loads(self.rfile.read(size))
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object")
        return value

    def session(self, csrf=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        item = cookie.get("webpulse_admin")
        if not item:
            return None
        with LOCK:
            result = SESSIONS.get(item.value)
            if result and result["expires"] < time.time():
                SESSIONS.pop(item.value, None)
                result = None
        if csrf and (not result or not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), result["csrf"])):
            return None
        return result

    def do_OPTIONS(self):
        if self.path_only() != "/api/feedback" or not self.origin_ok():
            return self.send(403, {"error": "Forbidden"})
        self.send(204, body=b"", headers=[("Access-Control-Allow-Methods", "POST, OPTIONS"),
                                            ("Access-Control-Allow-Headers", "Content-Type"),
                                            ("Access-Control-Max-Age", "600")])

    def do_GET(self):
        path = self.path_only()
        if path == "/healthz":
            return self.send(200, {"ok": True, "storage_configured": configured(),
                                   "email_configured": bool(env("RESEND_API_KEY") and env("RESEND_FROM"))})
        for route, filename, mime in [
            ("/admin.css", "admin.css", "text/css; charset=utf-8"),
            ("/admin.js", "admin.js", "application/javascript; charset=utf-8"),
            ("/admin", "index.html", "text/html; charset=utf-8"),
            ("/admin/", "index.html", "text/html; charset=utf-8"),
            ("/", "index.html", "text/html; charset=utf-8"),
        ]:
            if path == route:
                return self.send(200, body=ASSETS[filename], mime=mime)
        if path == "/api/admin/me":
            item = self.session()
            return self.send(200, {"authenticated": True, "csrf": item["csrf"]}) if item else self.send(401, {"authenticated": False})
        if path.startswith("/api/admin/"):
            if not self.session():
                return self.send(401, {"error": "Sign in required"})
            if not configured():
                return self.send(503, {"error": "Feedback database not configured"})
            try:
                if path == "/api/admin/users":
                    from urllib.parse import parse_qs
                    filters = parse_qs(urlsplit(self.path).query)
                    scope = filters.get("scope", ["accounts"])[0]
                    if scope not in {"accounts", "profiles"}:
                        return self.send(400, {"error": "Invalid directory scope"})
                    try:
                        offset = int(filters.get("offset", ["0"])[0])
                        if not 0 <= offset <= 1000000:
                            raise ValueError("Invalid offset")
                    except ValueError:
                        return self.send(400, {"error": "Invalid directory pagination"})
                    needle = filters.get("q", [""])[0].strip()[:100]
                    return self.send(200, admin_users(needle, offset, scope == "profiles"))
                rows = all_rows()
                if path == "/api/admin/feedback":
                    from urllib.parse import parse_qs
                    q = parse_qs(urlsplit(self.path).query)
                    status = q.get("status", ["all"])[0]
                    source = q.get("source", ["all"])[0]
                    needle = q.get("q", [""])[0].lower().strip()[:100]
                    if status not in (STATUSES | {"all"}) or source not in {"all", "website", "android"}:
                        return self.send(400, {"error": "Invalid filter"})
                    try:
                        limit = max(1, min(100, int(q.get("limit", ["40"])[0])))
                        offset = max(0, min(999, int(q.get("offset", ["0"])[0])))
                    except ValueError:
                        return self.send(400, {"error": "Invalid pagination"})
                    records = [r for r in rows if (status == "all" or r["status"] == status)
                               and (source == "all" or r["source"] == source)
                               and (not needle or needle in " ".join(str(r.get(x, "")) for x in ("message", "category", "page_url")).lower())]
                    return self.send(200, {"items": records[offset:offset+limit], "total": len(records)})
                if path == "/api/admin/stats":
                    return self.send(200, {"total": len(rows), **{s: sum(r.get("status") == s for r in rows) for s in STATUSES}})
                if path == "/api/admin/export.csv":
                    out = io.StringIO()
                    fields = ("id", "submitted_at", "updated_at", "source", "category", "message", "page_url", "status", "admin_note")
                    writer = csv.writer(out)
                    writer.writerow(fields)
                    for record in rows:
                        writer.writerow([("'" + str(record.get(k, "")) if str(record.get(k, "")).lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else record.get(k, "")) for k in fields])
                    return self.send(200, body=out.getvalue().encode("utf-8-sig"), mime="text/csv; charset=utf-8",
                                     headers=[("Content-Disposition", 'attachment; filename="webpulse-feedback.csv"')])
            except Exception:
                logging.error("Private admin directory unavailable" )
                return self.send(502, {"error": "Account directory unavailable. Retry shortly." if path == "/api/admin/users" else "Feedback database unavailable"})
        return self.send(404, {"error": "Not found"})

    def do_POST(self):
        path = self.path_only()
        if path == "/api/admin/login":
            if not self.origin_ok():
                return self.send(403, {"error": "Invalid origin"})
            if limited("login", self.client_address[0], 8, 900):
                return self.send(429, {"error": "Too many attempts"})
            password = env("WEBPULSE_ADMIN_PASSWORD")
            if len(password) < 12:
                return self.send(503, {"error": "Admin password not configured"})
            try:
                supplied = self.read_json(2048).get("password", "")
            except Exception:
                return self.send(400, {"error": "Invalid login request"})
            if not isinstance(supplied, str):
                return self.send(401, {"error": "Incorrect credentials"})
            hashed = lambda value: hashlib.pbkdf2_hmac("sha256", value.encode(), b"WebPulse-Admin-Password", 150_000)
            if not hmac.compare_digest(hashed(supplied), hashed(password)):
                return self.send(401, {"error": "Incorrect credentials"})
            token = secrets.token_urlsafe(36)
            csrf = secrets.token_urlsafe(32)
            with LOCK:
                SESSIONS[token] = {"expires": time.time() + SESSION_TTL, "csrf": csrf}
            return self.send(200, {"ok": True, "csrf": csrf}, headers=[("Set-Cookie", f"webpulse_admin={token}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}")])
        if path == "/api/admin/logout":
            if not self.session(csrf=True):
                return self.send(403, {"error": "Session/CSRF required"})
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            with LOCK:
                SESSIONS.pop(cookie["webpulse_admin"].value, None)
            return self.send(200, {"ok": True}, headers=[("Set-Cookie", "webpulse_admin=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0")])
        if path != "/api/feedback":
            return self.send(404, {"error": "Not found"})
        if not self.origin_ok():
            return self.send(403, {"saved": False, "error": "Origin not allowed"})
        if not configured():
            return self.send(503, {"saved": False, "error": "Feedback collection not yet configured"})
        if limited("feedback", self.client_address[0], 25, 3600):
            return self.send(429, {"saved": False, "error": "Too many submissions"})
        try:
            data = self.read_json()
        except Exception:
            return self.send(400, {"saved": False, "error": "Invalid feedback"})
        if data.get("website"):
            return self.send(200, {"saved": True})
        category, message, source = data.get("category", "Other"), data.get("message", ""), data.get("source", "website")
        page = data.get("pageUrl", "")
        if (category not in CATEGORIES or source not in {"website", "android"} or not isinstance(message, str)
            or not 8 <= len(message.strip()) <= 3000 or not isinstance(page, str) or len(page) > 1200):
            return self.send(400, {"saved": False, "error": "Invalid fields"})
        if page and (urlsplit(page).scheme not in {"http", "https"} or not urlsplit(page).netloc or "@" in urlsplit(page).netloc):
            return self.send(400, {"saved": False, "error": "Invalid page URL"})
        timestamp = now_utc()
        try:
            result = supabase("POST", payload={"submitted_at": timestamp, "updated_at": timestamp,
                "source": source, "category": category, "message": message.strip(), "page_url": page,
                "status": "pending", "admin_note": ""}, prefer="return=representation")
            record = {"id": result[0]["id"], "source": source, "category": category}
            notify(record)
            return self.send(201, {"saved": True, "id": record["id"]})
        except Exception:
            logging.exception("Feedback submission could not be stored")
            return self.send(502, {"saved": False, "error": "Could not store feedback. Please retry."})

    def do_PATCH(self):
        path = self.path_only()
        if not path.startswith("/api/admin/feedback/"):
            return self.send(404, {"error": "Not found"})
        if not self.session(csrf=True):
            return self.send(403, {"error": "Session/CSRF required"})
        if not configured():
            return self.send(503, {"error": "Database not configured"})
        try:
            ident = int(path.rsplit("/", 1)[-1])
            data = self.read_json()
            status, note = data.get("status"), data.get("admin_note", "")
            if ident <= 0 or status not in STATUSES or not isinstance(note, str) or len(note) > 2000:
                raise ValueError("Invalid update")
            result = supabase("PATCH", {"id": "eq." + str(ident)},
                              {"status": status, "admin_note": note, "updated_at": now_utc()},
                              prefer="return=representation")
            if not result:
                return self.send(404, {"error": "Feedback not found"})
            return self.send(200, {"ok": True})
        except (ValueError, TypeError):
            return self.send(400, {"error": "Invalid update"})
        except Exception:
            logging.exception("Feedback update failed")
            return self.send(502, {"error": "Could not update feedback"})


def run():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    port = int(os.getenv("PORT", "8000"))
    logging.info("WebPulse feedback API started on port %s; storage_configured=%s", port, configured())
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    run()

