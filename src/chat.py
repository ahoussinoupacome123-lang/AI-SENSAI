#!/usr/bin/env python3
"""Minimal Ollama CLI chatbot: streaming, in-session history, file system prompt."""
import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "chat_model": "qwen3:4b",
    "host": "http://localhost:11434",
    "chat_prompt_file": "prompts/chat_prompt.txt",
}


def load_config(path):
    config = dict(DEFAULTS)
    cfg_path = Path(path)
    if cfg_path.exists():
        try:
            config.update(json.loads(cfg_path.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            sys.exit(f"Error: cannot read config file {cfg_path}: {e}")
    return config


def load_system_prompt(path):
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        p = ROOT / p
    try:
        return p.read_text().strip()
    except OSError as e:
        sys.exit(f"Error: cannot read system prompt file {p}: {e}")


def stream_reply(host, model, messages):
    """Send the full history, print chunks as they arrive, return the full reply."""
    try:
        r = requests.post(
            f"{host}/api/chat",
            json={"model": model, "messages": messages, "stream": True},
            stream=True,
            timeout=(5, 300),
        )
    except requests.ConnectionError:
        raise RuntimeError(f"Cannot reach Ollama at {host}. Start it with: ollama serve")
    except requests.Timeout:
        raise RuntimeError("Ollama timed out.")

    if r.status_code == 404:
        raise RuntimeError(f"Model '{model}' not found. Pull it with: ollama pull {model}")
    if r.status_code != 200:
        raise RuntimeError(f"Ollama returned HTTP {r.status_code}: {r.text.strip()}")

    reply = []
    thinking_shown = False
    try:
        for line in r.iter_lines(chunk_size=1):
            if not line:
                continue
            chunk = json.loads(line)
            if "error" in chunk:
                raise RuntimeError(chunk["error"])
            message = chunk.get("message", {})
            if message.get("thinking") and not thinking_shown:
                print("(thinking...) ", end="", flush=True)  # Qwen3 reasons before answering
                thinking_shown = True
            text = message.get("content", "")
            print(text, end="", flush=True)
            reply.append(text)
            if chunk.get("done"):
                break
    finally:
        r.close()  # closing the connection makes Ollama stop generating
    print()
    return "".join(reply)


def main():
    parser = argparse.ArgumentParser(description="Ollama CLI chatbot")
    parser.add_argument("model", nargs="?", help="model name (overrides config)")
    parser.add_argument("--config", default=str(ROOT / "config.json"))
    parser.add_argument("--system-prompt", help="chat prompt file (overrides config)")
    args = parser.parse_args()

    config = load_config(args.config)
    model = args.model or config["chat_model"]
    host = config["host"].rstrip("/")
    system_prompt = load_system_prompt(args.system_prompt or config["chat_prompt_file"])

    messages = [{"role": "system", "content": system_prompt}]
    print(f"Chatting with {model}. Type 'exit' or Ctrl+D to quit; Ctrl+C cancels a reply.")
    print("Wait for the 'you>' prompt before typing: input typed while the model answers is queued.")

    while True:
        try:
            user_input = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            print("(empty input, please type something)")
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        messages.append({"role": "user", "content": user_input})
        print("bot> ", end="", flush=True)
        try:
            reply = stream_reply(host, model, messages)
        except RuntimeError as e:
            print(f"\nError: {e}")
            messages.pop()  # failed turn must not pollute the history
            continue
        except KeyboardInterrupt:
            print("\n(reply cancelled)")
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
