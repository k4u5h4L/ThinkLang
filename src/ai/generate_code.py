import src


def generate_code(prompt: str) -> str:
    print(prompt)
    src.interpreter.run("<stdin>", "a = 5")
    return """
for i in range(5):
    print(i)
"""
