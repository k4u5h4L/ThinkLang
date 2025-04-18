from src.interpreter import run, VERSION, ASCII_NAME
import os
import sys

os.environ["HF_HOME"] = __file__ + "./cache/models"


def handle_commands(args):
    if args[0] == "-h" or args[0] == "--help":
        print(f"Usage: {sys.argv[0]} [file]")
        print("If no file is specified, the interpreter will run in interactive mode.")
    else:
        path = str(args[0].replace("\\", "/"))
        fname = os.path.split(path)[0]
        if os.path.exists(path):
            with open(path, "r") as f:
                source_code = [line for line in f.readlines() if line.strip()]
        else:
            print(f"File '{fname}' does not exist")
            exit(1)
        for code in source_code:
            result, err = run(fname, code)
            if err:
                print(err)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0:
        handle_commands(args)
        exit(0)

    os.system("cls" if os.name == "nt" else "clear")
    print(ASCII_NAME)
    print("-" * 35)
    print(f"ThinkLang Shell {VERSION} - Python {sys.version.split('(')[0]}")
    print("-" * 35)
    print("Type 'help()' for a list of commands")
    while True:
        text = input("ThinkLang >> ")
        result, err = run("<stdin>", text)

        if text.strip() == "":
            continue

        if err:
            print(err)
        elif result:
            if len(result.elements) == 1:
                print(repr(result.elements[0]))
            else:
                print(repr(result))
