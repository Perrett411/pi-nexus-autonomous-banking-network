"""Restricted expression evaluator for smart contract code.

Replaces eval() so untrusted contract source can never execute arbitrary
Python. Only a safe subset of expression nodes is allowed; anything else
(attribute access, calls, imports, comprehensions, lambdas, ...) is
rejected with a ContractSandboxError.
"""
import ast
import operator as op


class ContractSandboxError(ValueError):
    """Raised when contract code uses disallowed syntax."""


_BINOPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow,
    ast.LShift: op.lshift, ast.RShift: op.rshift,
    ast.BitOr: op.or_, ast.BitXor: op.xor, ast.BitAnd: op.and_,
}
_UNARYOPS = {
    ast.USub: op.neg, ast.UAdd: op.pos, ast.Not: op.not_, ast.Invert: op.invert,
}
_CMPOPS = {
    ast.Eq: op.eq, ast.NotEq: op.ne, ast.Lt: op.lt, ast.LtE: op.le,
    ast.Gt: op.gt, ast.GtE: op.ge, ast.Is: op.is_, ast.IsNot: op.is_not,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
}
_CONSTANTS = (bool, int, float, complex, str, bytes, type(None))


def _eval(node, names):
    if isinstance(node, ast.Expression):
        return _eval(node.body, names)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, _CONSTANTS):
            return node.value
        raise ContractSandboxError(f"Unsupported constant: {type(node.value).__name__}")
    if isinstance(node, ast.Name):
        try:
            return names[node.id]
        except KeyError:
            raise ContractSandboxError(f"Unknown name: {node.id}") from None
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval(node.left, names), _eval(node.right, names))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return _UNARYOPS[type(node.op)](_eval(node.operand, names))
    if isinstance(node, ast.Compare):
        left = _eval(node.left, names)
        for cmp_op, comparator in zip(node.ops, node.comparators):
            if type(cmp_op) not in _CMPOPS:
                raise ContractSandboxError(f"Disallowed comparison: {type(cmp_op).__name__}")
            right = _eval(comparator, names)
            if not _CMPOPS[type(cmp_op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        result = isinstance(node.op, ast.And)  # start neutral for each branch
        for value in node.values:
            result = _eval(value, names)
            if isinstance(node.op, ast.And) and not result:
                return result
            if isinstance(node.op, ast.Or) and result:
                return result
        return result
    if isinstance(node, ast.IfExp):
        if _eval(node.test, names):
            return _eval(node.body, names)
        return _eval(node.orelse, names)
    if isinstance(node, ast.Subscript):
        return _eval(node.value, names)[_eval(node.slice, names)]
    if isinstance(node, ast.Tuple):
        return tuple(_eval(e, names) for e in node.elts)
    if isinstance(node, ast.List):
        return [_eval(e, names) for e in node.elts]
    if isinstance(node, ast.Set):
        return {_eval(e, names) for e in node.elts}
    if isinstance(node, ast.Dict):
        return {_eval(k, names): _eval(v, names)
                for k, v in zip(node.keys, node.values) if k is not None}
    raise ContractSandboxError(f"Disallowed syntax: {type(node).__name__}")


def safe_eval(code, names=None):
    """Safely evaluate a contract expression in the sandbox.

    `code` may only use literal constants, names from `names`, arithmetic /
    comparison / boolean operators, conditionals, subscripts and literal
    containers. Anything that could call code or reach attributes raises
    ContractSandboxError.
    """
    tree = ast.parse(code, mode='eval')
    return _eval(tree, names or {})
