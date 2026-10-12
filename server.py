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
    'admin.js': zlib.decompress(base64.b64decode('eNqdGNty2zb23V/BTD0BOaZpd7t9EYfxuI7TeidNPJbbvWQyDkQeSqghggUgOxpaM/vUH9iH/b9+yR4ABEnJkp3siw0B534/JAsFgdKS5Zqke7molA72gyxgRfaqEPliDpVOpqDPOZjjD8uLImRFlO5x0EGuZJkREgcSciELlX34GCvgkGsosmrBeSzKUoHOjmMtNOX4P9BsDtI+enaXpz+e34wv/nWe/fXY3xVUw5u5RkHuKF9AkL0KGi2XQSNBL2QVVHAfvEaY0D5HiRZvRU45jFGTahouqgJKVkERN0ugckQqVAR1JPFcVHo2ImompCZxQZeDt5lYIOhfDgs2Zfg4Z9VCQ3+xitJVTnU+80K0zJwIq5WXXWmqF+oaPuusqaEqEGZELt2BxKy6qaWYSlBqRC6qwP8gMf4V/A6KEblqTwRplosq10xUAYp8f1rXIRfTKRQXVdTsh4TW9a8M7kmU5Jwq9ZYpjbaYTjmEZMaKAioSv+gwUsTAH6x6FqdDWe1RtazyoBNDwu8LUDqsqZ7Fgai1yppV1OwFTvlZ1pDTPIdak5GRjjM0GeId/aYE0k2SJDQ4yUQUy5OGnKE7MKwOr5c1bENYjZB4jzUHPRPFy5eDHy+yjPx4fk2Q2D8Oz8ZXbw6vxS2qMDLBadHRiK1waOGM3lOmgxLQj06HJpeAOmtGOXpE0TkcCokOd9IaTvEMaAFSjRq8mPXStNcPD4YJRsdewMoQeSQuArIMA/rbly8NFyPlEa3ZES0wrI6sE0jUeJ+WyBuiVM+kuA/OpRQyJP/EaAwURoax+oyqAD7XDEVNgksO1GQtm1YBqwI6paxKCLqqVVOjMTMjRyugyd+Q5K2pzSuJHh4I6exinJGZ+4RVOV8UoEJizR+dOHMZYuYijEYuc42mL8ytuI2GUlu3JmDOyOHKxQpyWfAiqARyAvwxr7F4oCLEmKzNJYOY7j2KNlYxHUYm9ZuuMNDMC+UicWjYOaqW2rJkABNzSr2RtcQ0TR0uF7QIu3xed8Nqtefz5I2Qc8wTWhTnd2g7kypQATpHLSZzUyOcuJC9aiCpJRig11DSBUepu2yzpkEyGktCG/BYNdPW9rrKNtihWnI5tnXUBMJkobXxRYqgScEUnXAsr0abtLcL+gKZPmEZF3Jx47IGC9L78TWJjdlHfxu/f5coW8xYuQybGqvCPdbzEcrlzyiWrXMY6a2BHUdn4i2ARsNnLR9ipNg6ttNOCICJrhSdQrrCkk45XzZrhrBOs+nn6IiF/kFXW72WY3G5bZ0WRug0Y78nTYbEttuMNCtsCG38rNpGmG4EEsq0Ec9O+0E8l4xrTNHMNLRfrt6OsVvls0sq6VyFjasjxg3u9MYCewvHCitEDvbZnjaef7cvluBFVaMi/sE15VHbvtyvKOYMI9pfdj3ZuttK+oGjHWMjiPrYxtmlFHOmIEGnhB+2WbAEKCY0vz0hB62iUbwNzlIl0cco9ZOEYZYwDXOVutGBuzaFRxNt9rARKpZID9K23q1A7ZsBY9Wl78DbIAft2kD7Hr0V1j+2gJgdZ2JR6Q1YK+ABCfAsGSiCKuO0Iq/EvdrIC5xnpA4HGWBKUxdK4CayUNNpnHMVuzGkMXMZZN3ohs0Nx6TzHjZKsXQjfASu/b/Dhpfhb3NtSWCr6sYnBBqKbt/TtmLDQJahCm1ga9tU0BI+BswrFjF7j6aqOc3hbMZ4gciuWMK81ssnx5I2OhIO1dQ21eMoLbFGtrkUiNKPop0YcpctiJbExzarSpFB91CQGKfaT9/sN2XCitUntBkCJDidoJ5hB6fmGPgWtB1XwzJxjQG72w3VUYTqSo9mSHh+Ll/XOEapu3zMpaaoeZviASZS4o6xP+CcQWhVSMEKckJO3SlAMjhQ/R0mCrOIrEni0IY3m6qXCYYhTIVcRl7kuZpuyIs3j/ALdocETCc0EybS8ZE75IaInSEwcR7ZwdztNIMthM4M9hj34/YHf/fx4cEf1xU3lD1rakN3g3fbk23H7Z/aDhwTgWRMUcKjGaGDP//4r+nL9nl3vzGtxmC+Bk0ZD0uUyTH3cjkCQ0ndu8+W9lLLaGU7LfbK6Vs6Ab6ttJx8GmMXQohgv3G1/eDb1Z///k/3az2JViZp9huLuvo0Ih75uB0psEAZnuhR11W7vtuudpiDBqBCMbYCbLB75YQc1I41yzTd+miHisLeXzPNYXN+etOWleAbEwus6MHNXrgBvSM/e5yxTYkNrK9JsJ7UWZs5j4j5lOpBf5H8ERR6F24WkuP4/E6YymQH8mLA4GeXUo8w/ZjUK2UzoBvIfEr0AMgABs+2F9/gmA52O+jAdsyv+C7uQHK6XrMlzPG6q9nWyDkXCpyTEbbEgoyNYhADg/fQzoPbCGN+DaiufWewE/s6k53ZOABzstEqB/71eL2IO1HMXoBtFZsolVObK0O8aE1rnLO6RvWY4C0sC3FfDUjijYnLc5VTs89t0jIGUfTuC+zRT8Nmp/NmjVyXX19ShgS3bCPPBczT07afE47IgRcC03owfJ9en/20Y2PpB+VtkR/3gT3aGvtuqRlacG1Z2dhVdus4GNW+YFeRUGKJnT2zrBgRbLxtrABbEGa0wrJg203jP7ylrQqOxPqa8H+RWNsnHlNg9sURyDkCX7M54BYV2u9+2NDs5z+k6++3soq/+/64Zdh3nif7qyfxM9WzZE4/h8ftmnPYrzJrivQN60voHmQdmZ6KcSJ8roX8uoVz+7eoYSo4orha4zC1+/PUyo7y277CkLPug4sjFZyNf+2mG86q251DMUUwA5DMMDwz3EhbgPeT3zAl8XfYfxGacDEJoxbelCdjmYzcw6ReYJwf+oy2ijgoa5DQVO+1ADB80M/idsCnkyKKvzs+Po6e24zQH+5rUbr3P1T/GHM=')),
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
                logging.exception("Failed to load admin feedback")
                return self.send(502, {"error": "Feedback database unavailable"})
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
