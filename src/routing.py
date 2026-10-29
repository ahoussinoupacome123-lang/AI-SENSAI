"""Query intent routing and general knowledge / basic math fallback (D6).

Routes basic queries (math, greetings, general identity) to direct answers
so Sensai does not inappropriately refuse everyday basic requests with
'The document does not cover this'.
"""
import ast
import operator
import re

# Supported safe arithmetic operators
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_MATH_PREFIX_RE = re.compile(
    r"^\s*(?:what\s+is|how\s+much\s+is|combien\s+(?:font|vaut|fait)|calculate|compute)?\s*",
    re.IGNORECASE,
)
_MATH_SUFFIX_RE = re.compile(
    r"\s*(?:=\s*(?:combien|what|\?)?|\?|\s)*$",
    re.IGNORECASE,
)

_GREETING_MAP = {
    "hello": "Hello! I am Sensai, your local AI document assistant. How can I help you?",
    "hi": "Hi there! I am Sensai, your local AI assistant.",
    "hey": "Hello! How can I assist you with your documents today?",
    "bonjour": "Bonjour ! Je suis Sensai, votre assistant documentaire local.",
    "salut": "Salut ! Comment puis-je vous aider aujourd'hui ?",
    "good morning": "Good morning! How can I help you today?",
    "who are you": "I am Sensai, a local AI assistant designed to answer questions from your documents.",
    "qui es-tu": "Je suis Sensai, un assistant IA local conçu pour répondre à vos questions sur vos documents.",
    "what can you do": "I can analyze your PDF documents, retrieve relevant passages, answer questions with page citations, and chat with you locally.",
    "help": "You can ask me questions about your attached document, or ask general queries and calculations.",
    "aide": "Posez-moi des questions sur vos documents PDF, ou posez-moi des calculs et questions générales.",
}


def _safe_eval(node):
    """Safely evaluate an AST math expression without eval()."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _OPS:
            left = _safe_eval(node.left)
            right = _safe_eval(node.right)
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("division by zero")
            return _OPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _OPS:
            operand = _safe_eval(node.operand)
            return _OPS[op_type](operand)
    raise ValueError("Unsupported expression")


def is_math_query(text):
    """Return True if *text* is a simple arithmetic query."""
    if not isinstance(text, str) or not text.strip():
        return False
    # Strip common prefixes and suffixes
    cleaned = _MATH_PREFIX_RE.sub("", text.strip())
    cleaned = _MATH_SUFFIX_RE.sub("", cleaned).strip()
    if not cleaned:
        return False
    # Check that it contains at least one digit and an operator
    if not any(c.isdigit() for c in cleaned):
        return False
    if not any(c in "+-*/^%x×÷" for c in cleaned):
        return False
    # Replace non-standard math symbols
    norm = cleaned.replace("×", "*").replace("x", "*").replace("÷", "/").replace("^", "**")
    try:
        parsed = ast.parse(norm, mode="eval")
        _safe_eval(parsed)
        return True
    except ZeroDivisionError:
        return True
    except Exception:
        return False


def is_greeting_query(text):
    """Return True if *text* is a conversational greeting or identity query."""
    if not isinstance(text, str):
        return False
    cleaned = re.sub(r"[?!.,;:]", "", text.strip().lower())
    return any(cleaned == k or cleaned.startswith(f"{k} ") for k in _GREETING_MAP)


def is_general_query(text):
    """Return True if *text* is a general math or greeting/meta query."""
    return is_math_query(text) or is_greeting_query(text)


def solve_basic_query(text):
    """Return a Checked answer dict if *text* is a basic query, else None."""
    if not isinstance(text, str):
        return None

    # 1. Math query
    if is_math_query(text):
        cleaned = _MATH_PREFIX_RE.sub("", text.strip())
        cleaned = _MATH_SUFFIX_RE.sub("", cleaned).strip()
        norm = cleaned.replace("×", "*").replace("x", "*").replace("÷", "/").replace("^", "**")
        try:
            parsed = ast.parse(norm, mode="eval")
            res = _safe_eval(parsed)
            # Format integer nicely
            if isinstance(res, float) and res.is_integer():
                formatted = str(int(res))
            else:
                formatted = f"{res:.4g}" if isinstance(res, float) else str(res)
            return {
                "question": text,
                "answer": f"{formatted}",
                "page": 0,
                "quote": "",
                "status": "supported",
                "is_general": True,
            }
        except ZeroDivisionError:
            return {
                "question": text,
                "answer": "Cannot divide by zero.",
                "page": 0,
                "quote": "",
                "status": "supported",
                "is_general": True,
            }
        except Exception:
            return None

    # 2. Greeting / identity query
    if is_greeting_query(text):
        cleaned = re.sub(r"[?!.,;:]", "", text.strip().lower())
        for k, reply in _GREETING_MAP.items():
            if cleaned == k or cleaned.startswith(f"{k} "):
                return {
                    "question": text,
                    "answer": reply,
                    "page": 0,
                    "quote": "",
                    "status": "supported",
                    "is_general": True,
                }

    return None
