#!/usr/bin/env python3
"""A scripted stand-in for Ollama, used only to film the demo video (no model needed).

It speaks the few endpoints Sensai uses (/api/tags, /api/show, /api/embed, /api/chat) with
realistic delays, so the real web UI runs end to end exactly as it would with qwen3:4b:

- embeddings are hashed bags of words, enough for cosine search to find the right page;
- document answers come from a small table of key phrases about data/demo.pdf, and the quote
  is the sentence copied from the retrieved passage, so Sensai's own quote check really passes;
- the judge says "faithful" with a short reason; plain chat streams a canned Markdown reply.

    python scripts/demo_video/stub_ollama.py [--port 11555]
"""
import argparse
import hashlib
import json
import math
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIM = 512
STOP = set("a an the of to in on is are was what which who how does do and or for by with it its "
           "that this be as at from long many".split())

# (pattern in the question, key phrase that must be in a retrieved passage, short answer)
ANSWERS = [
    (r"ipv6", "128 bits long", "An IPv6 address is 128 bits long."),
    (r"dhcp", "Discover, Offer, Request and Acknowledge",
     "Discover, Offer, Request and Acknowledge, known as DORA."),
    (r"wi-?fi|channel", "1, 6 and 11", "Channels 1, 6 and 11 are the ones that do not overlap."),
    (r"ethernet|payload", "1500 bytes", "The maximum payload of an Ethernet frame is 1500 bytes (the MTU)."),
    (r"ssh", "port 22", "SSH uses port 22."),
    (r"ttl|time to live", "lifetime of a packet",
     "TTL limits the lifetime of a packet: each router decreases it by one and drops the packet at zero."),
    (r"vlan|802\.1q", "4 bytes long", "An 802.1Q VLAN tag is 4 bytes long, 12 bits of which hold the VLAN ID."),
]
REFUSAL = "The document does not cover this."

CHAT_REPLY = """**TCP** and **UDP** are the two transport protocols of the Internet.

| | TCP | UDP |
|---|---|---|
| Connection | set up first (handshake) | none |
| Delivery | reliable, in order | best effort |
| Speed | slower | faster |
| Typical use | web, email, SSH | video calls, DNS, games |

In short: use **TCP** when every byte matters, and **UDP** when speed matters more than a lost packet."""


def words(text):
    return [w.rstrip("s") for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


def vector(text):
    v = [0.0] * DIM
    for w in words(text):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def passages(prompt):
    """[(page, text)] parsed from Sensai's '[Passage i – page P]' blocks."""
    parts = re.split(r"\[Passage \d+ . page (\d+)\]\n", prompt)
    return [(int(parts[i]), parts[i + 1].split("\n\nQuestion:")[0]) for i in range(1, len(parts) - 1, 2)]


def sentence_with(text, phrase):
    """The whole sentence around phrase (a full stop inside a number such as 3.4 does not end it)."""
    i = text.find(phrase)
    starts = [m.end() for m in re.finditer(r"[.!?]\s+(?=[A-Z])", text[:i])]
    end = re.compile(r"[.!?](?=\s+[A-Z]|\s*$)").search(text, i + len(phrase))
    return text[starts[-1] if starts else 0:end.end() if end else len(text)].strip()


def document_answer(prompt):
    question = prompt.rsplit("Question:", 1)[-1].strip()
    found = passages(prompt)
    for pattern, phrase, short in ANSWERS:
        if re.search(pattern, question, re.I):
            for page, text in found:
                if phrase in text:
                    return {"answer": short, "page": page, "quote": sentence_with(text, phrase)}
    return {"answer": REFUSAL, "page": 0, "quote": ""}


def judge(prompt):
    answer = prompt.rsplit("Answer:", 1)[-1].strip()
    if answer.startswith(REFUSAL):
        return {"reason": "None of the passages answers the question, so the refusal is correct.", "verdict": "faithful"}
    return {"reason": "A passage states this directly, word for word.", "verdict": "faithful"}


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass  # clients closing keep-alive connections is normal here


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def send_json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/tags"):
            return self.send_json({"models": [{"name": "qwen3:4b"}, {"name": "nomic-embed-text:latest"}]})
        body = b"Ollama is running"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/api/show":
            return self.send_json({"model_info": {"qwen3.context_length": 40960}})
        if self.path == "/api/embed":
            texts = req["input"] if isinstance(req["input"], list) else [req["input"]]
            time.sleep(0.02 * len(texts))
            return self.send_json({"embeddings": [vector(t) for t in texts]})
        if self.path != "/api/chat":
            return self.send_json({"error": "not found"}, 404)
        prompt = req["messages"][-1]["content"]
        if req.get("format"):
            if "verdict" in json.dumps(req["format"]):
                time.sleep(0.9)
                out = judge(prompt)
            else:
                time.sleep(1.6)
                out = document_answer(prompt)
            return self.send_json({"message": {"role": "assistant", "content": json.dumps(out)}, "done": True})
        return self.stream_chat()

    def stream_chat(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def emit(obj):
            line = (json.dumps(obj) + "\n").encode()
            self.wfile.write(b"%x\r\n%s\r\n" % (len(line), line))
            self.wfile.flush()

        for _ in range(12):
            emit({"message": {"role": "assistant", "content": "", "thinking": "..."}, "done": False})
            time.sleep(0.1)
        for piece in re.findall(r"\S+\s*|\s+", CHAT_REPLY):
            emit({"message": {"role": "assistant", "content": piece}, "done": False})
            time.sleep(0.035)
        emit({"message": {"role": "assistant", "content": ""}, "done": True,
              "prompt_eval_count": 412, "eval_count": 168})
        self.wfile.write(b"0\r\n\r\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=11555)
    port = ap.parse_args().port
    print(f"stub Ollama on http://127.0.0.1:{port}", flush=True)
    Server(("127.0.0.1", port), Handler).serve_forever()
