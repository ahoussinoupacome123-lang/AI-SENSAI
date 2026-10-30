#!/usr/bin/env python3
"""Minimal Ollama CLI chatbot: streaming, in-session history, file system prompt."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `python src/chat.py` finds the src package

from src.memory import SessionMemory  # noqa: E402

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


def find_user_indices(messages):
    """Return 0-based indices of all user turns in messages."""
    return [i for i, m in enumerate(messages) if m.get("role") == "user"]


def edit_and_branch(messages, new_content, user_turn_number=None):
    """Fork conversation from a past user message and generate from the new prompt.

    Args:
        messages: List of message dictionaries [{'role': ..., 'content': ...}].
        new_content: The new text content for the edited turn.
        user_turn_number: 1-indexed number among user messages. If None, targets the last user message.

    Returns:
        (new_messages, archived_branch): The truncated/branched messages and a deep copy of the old history.
    """
    user_indices = find_user_indices(messages)
    if not user_indices:
        raise ValueError("No user messages in conversation to edit.")

    if user_turn_number is None:
        target_idx = user_indices[-1]
    else:
        if not isinstance(user_turn_number, int) or user_turn_number < 1 or user_turn_number > len(user_indices):
            raise ValueError(f"Turn number must be an integer between 1 and {len(user_indices)}.")
        target_idx = user_indices[user_turn_number - 1]

    archived = [dict(m) for m in messages]
    # Truncate messages up to the target turn and substitute new content
    new_messages = [dict(m) for m in messages[:target_idx]]
    new_messages.append({"role": "user", "content": str(new_content).strip()})
    return new_messages, archived


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
    branches = []
    memory = SessionMemory(embed_model=config.get("embed_model", "nomic-embed-text"), host=host)

    print(f"Chatting with {model}. Type 'exit' or Ctrl+D to quit; Ctrl+C cancels a reply.")
    print("Wait for the 'you>' prompt before typing: input typed while the model answers is queued.")
    print("Commands: /edit <text>, /history, /branches, /switch <n>, /memory, /recall <query>.")

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

        # Memory list command
        if user_input.lower() == "/memory":
            sessions = memory.list_sessions()
            if not sessions:
                print("(no saved memory sessions)")
            else:
                print(f"{len(sessions)} stored memory session(s):")
                for s in sessions:
                    print(f" - [{s['id']}] {s['title']} ({s['turn_count']} turns)")
            continue

        # Recall search command
        if user_input.lower().startswith("/recall"):
            query_str = user_input[7:].strip()
            if not query_str:
                print("(usage: /recall <query>)")
                continue
            try:
                matches = memory.search_memory(query_str, top_k=3)
                if not matches:
                    print("(no relevant memories found)")
                else:
                    for m in matches:
                        print(f" - [{m.get('session_title')}] (sim: {m.get('similarity')}) {m.get('role')}: {m.get('text')}")
            except Exception as e:
                print(f"Memory recall error: {e}")
            continue

        # History inspect command
        if user_input.lower() == "/history":
            user_indices = find_user_indices(messages)
            if not user_indices:
                print("(no user messages yet)")
            else:
                for num, u_idx in enumerate(user_indices, 1):
                    print(f"[{num}] {messages[u_idx]['content']}")
            continue

        # Branches inspect command
        if user_input.lower() == "/branches":
            if not branches:
                print("(no saved branches)")
            else:
                for b_idx, b in enumerate(branches, 1):
                    u_msgs = [m["content"] for m in b if m.get("role") == "user"]
                    last_preview = (u_msgs[-1][:30] + "...") if u_msgs else "empty"
                    print(f"[Branch {b_idx}] {len(b)} messages (last user: '{last_preview}')")
            continue

        # Switch branch command
        if user_input.lower().startswith("/switch"):
            parts = user_input.split()
            if len(parts) != 2 or not parts[1].isdigit():
                print("(usage: /switch <branch_number>)")
                continue
            b_num = int(parts[1])
            if b_num < 1 or b_num > len(branches):
                print(f"(branch {b_num} not found. Available: 1 to {len(branches)})")
                continue
            branches.append(list(messages))
            messages = branches.pop(b_num - 1)
            print(f"[Switched to branch {b_num}]")
            continue

        # Edit and branch command
        if user_input.lower().startswith("/edit"):
            cmd_args = user_input[5:].strip()
            if not cmd_args:
                print("(usage: /edit <new_text> or /edit <turn_number> <new_text>)")
                continue
            parts = cmd_args.split(maxsplit=1)
            if parts[0].isdigit() and len(parts) == 2:
                turn_num = int(parts[0])
                new_text = parts[1]
            elif parts[0].isdigit() and len(parts) == 1:
                print("(please specify the replacement text after turn number)")
                continue
            else:
                turn_num = None
                new_text = cmd_args

            try:
                new_messages, old_branch = edit_and_branch(messages, new_text, turn_num)
            except ValueError as e:
                print(f"Error: {e}")
                continue

            branches.append(old_branch)
            messages = new_messages
            print(f"[Branch created: editing turn {turn_num or len(find_user_indices(old_branch))}]")

            messages_to_send = list(messages)
            if memory.is_recall_query(new_text):
                try:
                    recalled = memory.search_memory(new_text, top_k=3)
                    if recalled:
                        block = memory.format_memory_context(recalled)
                        messages_to_send.insert(1, {"role": "system", "content": block})
                except Exception:
                    pass

            print("bot> ", end="", flush=True)
            try:
                reply = stream_reply(host, model, messages_to_send)
            except RuntimeError as e:
                print(f"\nError: {e}")
                continue
            except KeyboardInterrupt:
                print("\n(reply cancelled)")
                continue
            messages.append({"role": "assistant", "content": reply})
            continue

        messages.append({"role": "user", "content": user_input})

        messages_to_send = list(messages)
        if memory.is_recall_query(user_input):
            try:
                recalled = memory.search_memory(user_input, top_k=3)
                if recalled:
                    block = memory.format_memory_context(recalled)
                    messages_to_send.insert(1, {"role": "system", "content": block})
            except Exception:
                pass

        print("bot> ", end="", flush=True)
        try:
            reply = stream_reply(host, model, messages_to_send)
        except RuntimeError as e:
            print(f"\nError: {e}")
            messages.pop()  # failed turn must not pollute the history
            continue
        except KeyboardInterrupt:
            print("\n(reply cancelled)")
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": reply})

    # Save session to external memory on exit
    if find_user_indices(messages):
        try:
            first_user = next(m["content"] for m in messages if m.get("role") == "user")
            sid = f"cli_{int(datetime.now().timestamp())}"
            memory.save_session(sid, messages[1:], title=first_user[:36])
        except Exception:
            pass


if __name__ == "__main__":
    main()

