from src.interpreter import run, VERSION, ASCII_NAME
import os
import sys

from rich.console import Console

console = Console()


def handle_commands(args):
    if args[0] == "-h" or args[0] == "--help":
        console.print(f"Usage: {sys.argv[0]} [file]")
        console.print(
            "If no file is specified, the interpreter will run in interactive mode."
        )
    else:
        path = str(args[0].replace("\\", "/"))
        fname = os.path.split(path)[0]
        if os.path.exists(path):
            with open(path, "r") as f:
                source_code = [line for line in f.readlines() if line.strip()]
        else:
            console.print(f"File '{fname}' does not exist", style="bold red")
            exit(1)
        for code in source_code:
            result, err = run(fname, code)
            if err:
                console.print(err, style="bold red")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0:
        handle_commands(args)
        exit(0)

    # os.system("cls" if os.name == "nt" else "clear")
    console.clear()
    console.print(ASCII_NAME, style="blue")
    console.print("-" * 35, style="bold blue")
    console.print(f"ThinkLang Shell {VERSION} - Python {sys.version.split('(')[0]}")
    console.print("-" * 35, style="bold blue")
    console.print("Type 'help()' for a list of commands", style="white")
    while True:
        text = console.input(prompt="ThinkLang >> ")
        result, err = run("<stdin>", text)

        if text.strip() == "":
            continue

        if err:
            console.print(err, style="bold red")
        elif result:
            if len(result.elements) == 1:
                res = result.elements[0]
            else:
                res = result

            if type(res) == str:
                console.print(res, style="green")
            else:
                console.print(res)
