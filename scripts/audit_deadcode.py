"""AST audit: flag statements that follow a return at the same body level.

Such code indicates template/append corruption (dead code that Python allows
but never executes).
"""

import ast
import pathlib
import sys


def bodies(node):
    for field in ("body", "orelse", "finalbody"):
        value = getattr(node, field, None)
        if isinstance(value, list):
            yield field, value


def check(path: pathlib.Path) -> list[str]:
    issues = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"SYNTAX ERROR: {exc}"]

    for parent in ast.walk(tree):
        for field, body in bodies(parent):
            for index, stmt in enumerate(body):
                if isinstance(stmt, (ast.Return, ast.Break, ast.Continue)):
                    later = body[index + 1:]
                    # Ignore trailing Ellipsis/Expr constants (docstring-ish)
                    real = [s for s in later
                            if not (isinstance(s, ast.Expr)
                                    and isinstance(s.value, ast.Constant))]
                    if real:
                        where = getattr(parent, "name", "<module>")
                        issues.append(
                            f"{field} of {where}: unreachable line {real[0].lineno} "
                            f"({type(real[0]).__name__})"
                        )
    return issues


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    total = 0
    for path in sorted(root.rglob("*.py")):
        if any(part in {".venv", "__pycache__", "migrations", "node_modules"}
               for part in path.parts):
            continue
        issues = check(path)
        if issues:
            total += len(issues)
            print(path.relative_to(root))
            for issue in issues:
                print("   ", issue)
    print("total issues:", total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
