"""Vansh's calculator: the small application the Session 16 pipeline tests, builds and ships."""

OPERATIONS = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide", "^": "power"}


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(a, b):
    return a ** b


def calculate(expression):
    """Evaluate one line like '10 + 5' and return the result."""
    parts = expression.split()
    if len(parts) != 3 or parts[1] not in OPERATIONS:
        raise ValueError("Use the form: <number> <+ - * / ^> <number>")
    a, op, b = float(parts[0]), parts[1], float(parts[2])
    result = globals()[OPERATIONS[op]](a, b)
    return int(result) if float(result).is_integer() else result


def main():
    print("Vansh's calculator. Type an expression like '10 + 5', or q to quit.")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if line.lower() in ("q", "quit", "exit"):
            break
        try:
            print(f"{line} = {calculate(line)}")
        except ValueError as err:
            print(f"error: {err}")
    print("bye")


if __name__ == "__main__":
    main()
