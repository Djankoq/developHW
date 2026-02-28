import ast
import operator
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Smart Calculator API",
    description="API для базовых вычислений и парсинга сложных математических выражений."
)

app.state.current_expression = ""


class BasicMath(BaseModel):
    a: float
    b: float


class ExpressionSet(BaseModel):
    expression: str


class ExecuteRequest(BaseModel):
    variables: Optional[Dict[str, float]] = None


@app.post("/add", summary="Сложение")
def add(data: BasicMath):
    return {"result": data.a + data.b}


@app.post("/sub", summary="Вычитание")
def sub(data: BasicMath):
    return {"result": data.a - data.b}


@app.post("/mul", summary="Умножение")
def mul(data: BasicMath):
    return {"result": data.a * data.b}


@app.post("/div", summary="Деление")
def div(data: BasicMath):
    if data.b == 0:
        raise HTTPException(status_code=400, detail="Ошибка: Деление на ноль.")
    return {"result": data.a / data.b}


def safe_evaluate(expr: str, variables: Optional[Dict[str, float]] = None) -> float:
    if variables is None:
        variables = {}

    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # Для старых версий Python
            return node.n
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return float(variables[node.id])
            raise ValueError(f"Не задано значение для переменной: '{node.id}'")
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)

            if op_type == ast.Div and right == 0:
                raise ValueError("Деление на ноль в выражении.")
            if op_type not in allowed_operators:
                raise ValueError(f"Неподдерживаемый оператор: {op_type}")

            return allowed_operators[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            return allowed_operators[type(node.op)](operand)
        else:
            raise ValueError("Обнаружен неподдерживаемый синтаксис.")

    try:
        tree = ast.parse(expr, mode='eval')
        return _eval(tree.body)
    except SyntaxError:
        raise ValueError("Синтаксическая ошибка. Проверьте правильность выражения.")


@app.post("/expression", summary="Задать текущее выражение")
def set_expression(data: ExpressionSet):
    app.state.current_expression = data.expression
    return {
        "message": "Выражение успешно сохранено.",
        "current_expression": app.state.current_expression
    }


@app.get("/expression", summary="Посмотреть текущее выражение")
def get_expression():
    return {
        "current_expression": app.state.current_expression
    }


@app.post("/execute", summary="Выполнить текущее выражение")
def execute_expression(data: ExecuteRequest = ExecuteRequest()):
    expr = app.state.current_expression
    if not expr:
        raise HTTPException(status_code=400, detail="Выражение не задано. Сначала используйте POST /expression.")

    try:
        result = safe_evaluate(expr, data.variables)
        return {
            "expression": expr,
            "variables_used": data.variables or {},
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка вычисления: {str(e)}")
