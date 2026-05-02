"""Safe math calculator and crypto price calculator."""

from __future__ import annotations

import ast
import operator
import re

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}

MATH_PATTERN = re.compile(
    r"^[\d\s\+\-\*\/\.\(\)\%\^]+={0,1}$"
)

CRYPTO_QTY_PATTERN = re.compile(
    r"^([\d,]+(?:\.\d+)?)\s*([a-zA-Z]{2,10})(?:\s*=)?$"
)


def _safe_eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPS:
            raise ValueError(f"Unsupported operator: {op_type}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        if op_type is ast.Pow and right > 100:
            raise ValueError("Exponent too large")
        return SAFE_OPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPS:
            raise ValueError(f"Unsupported operator: {op_type}")
        return SAFE_OPS[op_type](_safe_eval_node(node.operand))
    raise ValueError("Unsupported expression")


def try_math(text: str) -> str | None:
    expr = text.rstrip("=").strip()
    if not MATH_PATTERN.match(text):
        return None
    expr = expr.replace("^", "**")
    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval_node(tree.body)
        if result == int(result):
            return f"<b>{text.rstrip('=').strip()}</b> = <code>{int(result)}</code>"
        return f"<b>{text.rstrip('=').strip()}</b> = <code>{result:.8g}</code>"
    except Exception:
        return None


def parse_crypto_qty(text: str) -> tuple[float, str] | None:
    m = CRYPTO_QTY_PATTERN.match(text.strip())
    if m:
        qty = float(m.group(1).replace(",", ""))
        symbol = m.group(2).lower()
        if qty > 0:
            return qty, symbol
    return None
