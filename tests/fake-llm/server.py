#!/usr/bin/env python3
# Фиктивный OpenAI-совместимый API для проверки cliproxyapi (только stdlib).
# Запуск: python3 -I server.py  -> слушает 127.0.0.1:19999
# Эндпоинты: GET /v1/models, POST /v1/chat/completions (stream true/false), POST /v1/responses (stream true/false).
# Ключи и тела запросов в лог не пишутся.
import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 19999
DELAY = 0.3
MODELS = ["fake-upstream-a", "fake-upstream-b"]
PIECES = ["Hello", ", this", " is", " a", " fake", " streamed", " reply", "."]
FULL_TEXT = "".join(PIECES)


def now():
    return int(time.time())


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "fake-llm/1"

    def log_message(self, fmt, *args):
        # Только метод и путь: заголовки (Authorization) и тела не логируем.
        sys.stderr.write("%s %s %s\n" % (time.strftime("%H:%M:%S"), self.command, self.path))

    # ---- helpers ----
    def _read_body(self):
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            raw = b""
            while True:
                size = int(self.rfile.readline().strip(), 16)
                if size == 0:
                    self.rfile.readline()
                    break
                raw += self.rfile.read(size)
                self.rfile.readline()
        else:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw or b"{}")
        except ValueError:
            return {}

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _sse_start(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def _sse_write(self, payload):
        data = payload.encode()
        self.wfile.write(b"%x\r\n%s\r\n" % (len(data), data))
        self.wfile.flush()

    def _sse_end(self):
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    # ---- routes ----
    def do_GET(self):
        if self.path in ("/healthz", "/v1/healthz"):
            self._json(200, {"status": "ok"})
        elif self.path == "/v1/models":
            self._json(200, {
                "object": "list",
                "data": [{"id": m, "object": "model", "created": now(), "owned_by": "fake"} for m in MODELS],
            })
        else:
            self._json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            self._chat()
        elif self.path == "/v1/responses":
            self._responses()
        else:
            self._read_body()
            self._json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def _chat(self):
        body = self._read_body()
        model = body.get("model") or MODELS[0]
        cid = "chatcmpl-fake-" + uuid.uuid4().hex[:12]
        if not body.get("stream"):
            self._json(200, {
                "id": cid, "object": "chat.completion", "created": now(), "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": FULL_TEXT},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": len(PIECES), "total_tokens": 1 + len(PIECES)},
            })
            return

        def chunk(delta, finish=None):
            return "data: " + json.dumps({
                "id": cid, "object": "chat.completion.chunk", "created": now(), "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }) + "\n\n"

        events = [chunk({"role": "assistant", "content": ""})]
        events += [chunk({"content": p}) for p in PIECES]
        events += [chunk({}, "stop"), "data: [DONE]\n\n"]
        self._sse_start()
        for i, ev in enumerate(events):
            if i:
                time.sleep(DELAY)
            self._sse_write(ev)
        self._sse_end()

    def _responses(self):
        body = self._read_body()
        model = body.get("model") or MODELS[0]
        rid = "resp_fake_" + uuid.uuid4().hex[:12]
        if not body.get("stream"):
            self._json(200, {
                "id": rid, "object": "response", "created_at": now(), "model": model, "status": "completed",
                "output": [{"type": "message", "id": "msg_fake", "status": "completed", "role": "assistant",
                            "content": [{"type": "output_text", "text": FULL_TEXT, "annotations": []}]}],
                "usage": {"input_tokens": 1, "output_tokens": len(PIECES), "total_tokens": 1 + len(PIECES)},
            })
            return

        def ev(name, data):
            data = dict(data, type=name)
            return "event: %s\ndata: %s\n\n" % (name, json.dumps(data))

        events = [ev("response.created", {"response": {"id": rid, "object": "response", "model": model,
                                                        "status": "in_progress"}})]
        events += [ev("response.output_text.delta", {"item_id": "msg_fake", "output_index": 0,
                                                     "content_index": 0, "delta": p}) for p in PIECES]
        events += [ev("response.output_text.done", {"item_id": "msg_fake", "output_index": 0,
                                                    "content_index": 0, "text": FULL_TEXT})]
        events += [ev("response.completed", {"response": {"id": rid, "object": "response", "model": model,
                                                           "status": "completed"}})]
        self._sse_start()
        for i, e in enumerate(events):
            if i:
                time.sleep(DELAY)
            self._sse_write(e)
        self._sse_end()


if __name__ == "__main__":
    ThreadingHTTPServer.daemon_threads = True
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.serve_forever()
