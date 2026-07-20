from typing import Any


class ConditionEvaluationError(Exception):
    pass


SUPPORTED_OPERATORS = {
    "equals",
    "not_equals",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "contains",
}


def evaluate_condition(expression: dict, data: dict) -> bool:
    field = expression.get("field")
    operator = expression.get("operator")
    expected = expression.get("value")

    if not isinstance(field, str) or not field:
        raise ConditionEvaluationError("Condition field is required")
    if operator not in SUPPORTED_OPERATORS:
        raise ConditionEvaluationError("Unsupported condition operator")

    actual = read_path(data, field)

    try:
        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "greater_than":
            return actual > expected
        if operator == "greater_than_or_equal":
            return actual >= expected
        if operator == "less_than":
            return actual < expected
        if operator == "less_than_or_equal":
            return actual <= expected
        if operator == "contains":
            return expected in actual
    except TypeError:
        return False

    raise ConditionEvaluationError("Unsupported condition operator")


def read_path(data: dict, path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current
