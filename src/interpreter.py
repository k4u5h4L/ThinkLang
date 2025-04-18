#######################################
# Imports
#######################################

import os
import time
import random
from .ai.generate_code import generate_code
from .lib.parser import Parser

from .consts import *
from .lib.error import (
    Error,
    RTError,
    InvalidSyntaxError,
    KeyboardInterruptError,
    position_start,
    position_end,
)
from .lib.nodes import *
from .lib.parsing_types import *
from .lib.lex import Lexer, RTResult
from .lib.parsing_types import *
from .lib.utils import Token
import os
from pathlib import Path

# global vars
BUILTIN_FUNCTIONS = []
global_symbol_table = SymbolTable()


def import_module(fn, interpreter, context):
    # Generate tokens
    res = RTResult()
    result = None
    fpath = Path(fn)
    # check if file exists
    if not fpath.is_file():
        return None, res.failure(
            RTError(position_start, position_end, "File not found", context)
        )

    with open(fn, "r") as f:
        text = f.read()

    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error

    try:
        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return None, ast.error

        # Run program

        context = Context(f"<{fpath.stem}>")
        context.symbol_table = global_symbol_table
        context.private_symbol_table = SymbolTable()
        context.private_symbol_table.set("is_main", Number(0))
        result = interpreter.visit(ast.node, context)
        result.value = "" if str(result.value) == "null" else result.value
        return result.value, result.error
    except KeyboardInterrupt:
        err = KeyboardInterruptError(
            position_start, position_end, "Execution interrupted"
        )
        return None, err


class Function(BaseFunction):
    """
    Function Base Class
    """

    __slots__ = ("body_node", "arg_names", "should_auto_return")

    def __init__(self, name, body_node, arg_names, should_auto_return):
        super().__init__(name)
        self.body_node = body_node
        self.arg_names = arg_names
        self.should_auto_return = should_auto_return

    def execute(self, args):
        res = RTResult()
        interpreter = Interpreter()
        exec_ctx = self.generate_new_context()

        res.register(self.check_and_populate_args(self.arg_names, args, exec_ctx))
        if res.should_return():
            return res

        value = res.register(interpreter.visit(self.body_node, exec_ctx))
        if res.should_return() and res.func_return_value == None:
            return res

        ret_value = (
            (value if self.should_auto_return else None)
            or res.func_return_value
            or Null.null
        )
        return res.success(ret_value)

    def copy(self):
        copy = Function(
            self.name, self.body_node, self.arg_names, self.should_auto_return
        )
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def type(self):
        return "<function>"

    def __repr__(self):
        return f"<function {self.name}>"


class BuiltInFunction(BaseFunction):
    def __init__(self, name):
        super().__init__(name)

    def execute(self, args):
        res = RTResult()
        exec_ctx = self.generate_new_context()

        method_name = f"execute_{self.name}"
        method = getattr(self, method_name, self.no_visit_method)

        res.register(self.check_and_populate_args(method.arg_names, args, exec_ctx))
        if res.should_return():
            return res

        return_value = res.register(method(exec_ctx))
        if res.should_return():
            return res
        return res.success(return_value)

    def no_visit_method(self, node, context):
        raise Exception(f"No execute_{self.name} method defined")

    def copy(self):
        copy = BuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function {self.name}>"

    ###############- builtin funcitons -#####################

    def execute_print(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        if isinstance(value, String):
            print(value.value)
            return RTResult().success(Null.null)

        print(repr(exec_ctx.symbol_table.get("value")))
        return RTResult().success(Null.null)

    execute_print.arg_names = ["value"]

    def execute_gets(self, exec_ctx):
        prompt = exec_ctx.symbol_table.get("prompt")
        text = input(prompt)
        return RTResult().success(String(text))

    execute_gets.arg_names = ["prompt"]

    def execute_clear(self, exec_ctx):
        os.system("cls" if os.name == "nt" else "clear")
        return RTResult().success(Null.null)

    execute_clear.arg_names = []

    def execute_type_of(self, exec_ctx):
        data = exec_ctx.symbol_table.get("value")
        return RTResult().success(String(data.type()))

    execute_type_of.arg_names = ["value"]

    def execute_is_number(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), Number)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_number.arg_names = ["value"]

    def execute_is_string(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), String)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_string.arg_names = ["value"]

    def execute_is_list(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), List)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_list.arg_names = ["value"]

    def execute_is_function(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), BaseFunction)
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_function.arg_names = ["value"]

    def execute_tostr(self, exec_ctx):
        return RTResult().success(String(str(exec_ctx.symbol_table.get("value"))))

    execute_tostr.arg_names = ["value"]

    def execute_append(self, exec_ctx):
        # this works for list and strings
        obj_ = exec_ctx.symbol_table.get("object")
        value = exec_ctx.symbol_table.get("value")

        if isinstance(obj_, List):
            obj_.elements.append(value)
            return RTResult().success(value)
        elif isinstance(obj_, String):
            return RTResult().success(String(obj_.value + value.value))
        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Invalid argument for 'append'",
                    exec_ctx,
                )
            )

    execute_append.arg_names = ["object", "value"]

    def execute_pop(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")
        index = exec_ctx.symbol_table.get("index")

        if not isinstance(list_, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'pop' must be list",
                    exec_ctx,
                )
            )

        if not isinstance(index, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'pop' must be number",
                    exec_ctx,
                )
            )

        try:
            element = list_.elements.pop(index.value)
        except:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Element at this index could not be removed from list because index is out of bounds",
                    exec_ctx,
                )
            )
        return RTResult().success(element)

    execute_pop.arg_names = ["list", "index"]

    def execute_extend(self, exec_ctx: Context):
        listA = exec_ctx.symbol_table.get("listA")
        listB = exec_ctx.symbol_table.get("listB")

        if not isinstance(listA, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'extend' must be list",
                    exec_ctx,
                )
            )

        if not isinstance(listB, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'extend' must be list",
                    exec_ctx,
                )
            )

        listA.elements.extend(listB.elements)
        return RTResult().success(Null.null)

    execute_extend.arg_names = ["listA", "listB"]

    def execute_replace(self, exec_ctx):
        string = exec_ctx.symbol_table.get("string")
        value = exec_ctx.symbol_table.get("value")
        with_val = exec_ctx.symbol_table.get("with")

        if not isinstance(string, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of 'replace' must be string",
                    exec_ctx,
                )
            )
        if not isinstance(value, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument of 'replace' must be string",
                    exec_ctx,
                )
            )
        if not isinstance(with_val, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Third argument of 'replace' must be string",
                    exec_ctx,
                )
            )
        val = string.value.replace(value.value, with_val.value)
        return RTResult().success(String(val))

    execute_replace.arg_names = ["string", "value", "with"]

    def execute_len(self, exec_ctx):
        value_ = exec_ctx.symbol_table.get("value")

        if isinstance(value_, List):
            return RTResult().success(Number(len(value_.elements)))
        elif isinstance(value_, String):
            return RTResult().success(Number(len(value_.value)))
        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Argument for 'len' must be list or string",
                    exec_ctx,
                )
            )

    execute_len.arg_names = ["value"]

    def execute_run(self, exec_ctx):
        fn = exec_ctx.symbol_table.get("fn")

        if not isinstance(fn, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument must be string",
                    exec_ctx,
                )
            )

        fn = fn.value

        try:
            with open(fn, "r") as f:
                script = f.read()
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to load script "{fn}"\n' + str(e),
                    exec_ctx,
                )
            )

        _, error = run(fn, script)

        if error:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to finish executing script "{fn}"\n' + str(error),
                    exec_ctx,
                )
            )

        return RTResult().success(Null.null)

    execute_run.arg_names = ["fn"]

    def execute_sleep(self, exec_ctx):
        seconds = exec_ctx.symbol_table.get("seconds")

        if not isinstance(seconds, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'sleep' must be a number",
                    exec_ctx,
                )
            )

        time.sleep(seconds.value)
        return RTResult().success(Null.null)

    execute_sleep.arg_names = ["seconds"]

    def execute_exit(self, exec_ctx):
        exit(0)

    execute_exit.arg_names = []

    def execute_open_file(self, exec_ctx):
        file_path = exec_ctx.symbol_table.get("file_path")

        if not isinstance(file_path, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'open_stream' must be a string",
                    exec_ctx,
                )
            )

        try:
            file_name = os.path.splitext(file_path.value)[0]
            return RTResult().success(File(file_name, file_path.value))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to open file "{file_path.value}"\n' + str(e),
                    exec_ctx,
                )
            )

    execute_open_file.arg_names = ["file_path"]

    def execute_read_stream(self, exec_ctx):
        file = exec_ctx.symbol_table.get("file")

        if not isinstance(file, File):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'read_stream' must be a file",
                    exec_ctx,
                )
            )

        try:
            with open(file.path, "r") as f:
                return RTResult().success(String(f.read()))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to read file "{file.path}"\n' + str(e),
                    exec_ctx,
                )
            )

    execute_read_stream.arg_names = ["file"]

    def execute_write_stream(self, exec_ctx):
        file = exec_ctx.symbol_table.get("file")
        text = exec_ctx.symbol_table.get("text")

        if not isinstance(file, File):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'write_stream' must be a file",
                    exec_ctx,
                )
            )

        if not isinstance(text, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'write_stream' must be a string",
                    exec_ctx,
                )
            )

        try:
            with open(file.path, "a") as f:
                f.write(text.value)
            return RTResult().success(Number.null)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to write to file "{file.path}"\n' + str(e),
                    exec_ctx,
                )
            )

    execute_write_stream.arg_names = ["file", "text"]

    def execute_file_exists(self, exec_ctx):
        file_path = exec_ctx.symbol_table.get("file_path")

        if isinstance(file_path, String):
            file_path = file_path.value

        elif isinstance(file_path, File):
            file_path = file_path.path

        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'file_exists' must be a string or file",
                    exec_ctx,
                )
            )

        try:
            return RTResult().success(
                Number.true if os.path.exists(file_path) else Number.false
            )
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to check if file exists "{file_path}"\n' + str(e),
                    exec_ctx,
                )
            )

    execute_file_exists.arg_names = ["file_path"]

    def execute_get_now(self, exec_ctx):
        return RTResult().success(Number(time.time()))

    execute_get_now.arg_names = []

    def execute_get_env(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")

        if not isinstance(name, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'get_env' must be a string",
                    exec_ctx,
                )
            )

        value = os.getenv(name.value)

        if value is None:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Environment variable '{name.value}' not found",
                    exec_ctx,
                )
            )

        return RTResult().success(String(value))

    execute_get_env.arg_names = ["name"]

    def execute_set_env(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")
        value = exec_ctx.symbol_table.get("value")

        if not isinstance(name, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'set_env' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(value, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'set_env' must be a string",
                    exec_ctx,
                )
            )

        try:
            os.environ[name.value] = value.value
            return RTResult().success(Null.null)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set environment variable '{name.value}'\n" + str(e),
                    exec_ctx,
                )
            )

    execute_set_env.arg_names = ["name", "value"]

    def execute_get_dir(self, exec_ctx):
        try:
            return RTResult().success(String(os.getcwd()))
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to get current directory\n" + str(e),
                    exec_ctx,
                )
            )

    execute_get_dir.arg_names = []

    def execute_set_dir(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")

        if not isinstance(name, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'set_dir' must be a string",
                    exec_ctx,
                )
            )

        try:
            os.chdir(name.value)
            return RTResult().success(Null.null)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to set current directory to '{name.value}'\n" + str(e),
                    exec_ctx,
                )
            )

    execute_set_dir.arg_names = ["name"]

    def execute_random(self, exec_ctx):
        return RTResult().success(Number(random.random()))

    execute_random.arg_names = []

    def execute_rand_int(self, exec_ctx):
        min = exec_ctx.symbol_table.get("min")
        max = exec_ctx.symbol_table.get("max")

        if not isinstance(min, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'rand_int' must be a number",
                    exec_ctx,
                )
            )

        if not isinstance(max, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'rand_int' must be a number",
                    exec_ctx,
                )
            )

        return RTResult().success(Number(random.randint(min.value, max.value)))

    execute_rand_int.arg_names = ["min", "max"]

    def execute_rand_seed(self, exec_ctx):
        seed = exec_ctx.symbol_table.get("seed")

        if not isinstance(seed, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'rand_seed' must be a number",
                    exec_ctx,
                )
            )

        random.seed(seed.value)
        return RTResult().success(Null.null)

    execute_rand_seed.arg_names = ["seed"]

    def execute_rand_pick(self, exec_ctx):
        arr = exec_ctx.symbol_table.get("arr")

        if not isinstance(arr, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'rand_pick' must be an List",
                    exec_ctx,
                )
            )

        if len(arr.elements) == 0:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Array passed to 'rand_pick' is empty",
                    exec_ctx,
                )
            )

        return RTResult().success(
            arr.elements[random.randrange(0, len(arr.elements) - 1)]
        )

    execute_rand_pick.arg_names = ["arr"]

    def execute_toint(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        supress_error = exec_ctx.symbol_table.get("supress_error")

        if not isinstance(supress_error, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'toint' must be a number",
                    exec_ctx,
                )
            )

        if supress_error.value == 1:
            supress_error = True
        elif supress_error.value == 0:
            supress_error = False
        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'toint' must be a boolean",
                    exec_ctx,
                )
            )

        if isinstance(value, Number):
            return RTResult().success(Number(int(value.value)))
        elif isinstance(value, String):
            try:
                return RTResult().success(Number(int(value.value)))
            except ValueError:
                if supress_error:
                    return RTResult().success(Number.null)
                else:
                    return RTResult().failure(
                        RTError(
                            self.pos_start,
                            self.pos_end,
                            f"Failed to convert '{value.value}' of type '{value.type()}' to integer",
                            exec_ctx,
                        )
                    )
        else:
            if supress_error:
                return RTResult().success(Number.null)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"Failed to convert value of type '{value.type()}' to integer",
                        exec_ctx,
                    )
                )

    execute_toint.arg_names = ["value", "supress_error"]

    def execute_tofloat(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        supress_error = exec_ctx.symbol_table.get("supress_error")

        if not isinstance(supress_error, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'tofloat' must be a number",
                    exec_ctx,
                )
            )

        if supress_error.value == 1:
            supress_error = True
        elif supress_error.value == 0:
            supress_error = False
        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'tofloat' must be a boolean",
                    exec_ctx,
                )
            )

        if isinstance(value, Number):
            return RTResult().success(Number(float(value.value)))
        elif isinstance(value, String):
            try:
                return RTResult().success(Number(float(value.value)))
            except ValueError:
                if supress_error:
                    return RTResult().success(Number.null)
                else:
                    return RTResult().failure(
                        RTError(
                            self.pos_start,
                            self.pos_end,
                            f"Failed to convert '{value.value}' of type '{value.type()}' to float",
                            exec_ctx,
                        )
                    )
        else:
            if supress_error:
                return RTResult().success(Number.null)
            else:
                return RTResult().failure(
                    RTError(
                        self.pos_start,
                        self.pos_end,
                        f"Failed to convert value of type '{value.type()}' to float",
                        exec_ctx,
                    )
                )

    execute_tofloat.arg_names = ["value", "supress_error"]

    def execute_join(self, exec_ctx):
        # join list with a sep
        sep = exec_ctx.symbol_table.get("sep")
        iterables = exec_ctx.symbol_table.get("elements")
        if not isinstance(sep, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'join' must be a string",
                    exec_ctx,
                )
            )

        if isinstance(iterables, List):
            if len(iterables.elements) == 0:
                return RTResult().success(String(""))

            return RTResult().success(
                String(
                    sep.value.join(
                        [str(element.value) for element in iterables.elements]
                    )
                )
            )
        elif isinstance(iterables, String):
            if len(iterables) == 0:
                return RTResult().success(String(""))
            return RTResult().success(
                String(sep.value.join([str(element) for element in iterables.value]))
            )
        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'join' must be a list or a string",
                    exec_ctx,
                )
            )

    execute_join.arg_names = ["sep", "elements"]

    def execute_help_for(self, exec_ctx):
        name = exec_ctx.symbol_table.get("funcname")
        if isinstance(name, String):
            if name.value == "":
                return RTResult().success(String(helpMsg))
            elif name.value in help_dict:
                c = help_dict[name.value]
                text = f"""
                \r-{c['text']}
                \r\t- args: {c['args']}
                \r\t- returns: {c['returns']}
                """.strip()
                return RTResult().success(String(text))
            else:
                RTResult().success(String("No Help Available"))
        else:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'help' must be a string",
                    exec_ctx,
                )
            )

    execute_help_for.arg_names = ["funcname"]

    def execute_help(self, exec_ctx):
        return RTResult().success(String(helpMsg))

    execute_help.arg_names = []

    def execute_sys(self, exec_ctx):
        command = exec_ctx.symbol_table.get("command")

        if not isinstance(command, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'sys' must be a string",
                    exec_ctx,
                )
            )

        try:
            os.system(command.value)
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f"Failed to execute '{command.value}'\n" + str(e),
                    exec_ctx,
                )
            )

        return RTResult().success(Null.null)

    execute_sys.arg_names = ["command"]

    def execute_version(self, _):
        return RTResult().success(String(VERSION))

    execute_version.arg_names = []

    def execute_error(self, exec_ctx):
        msg = exec_ctx.symbol_table.get("message")

        if not isinstance(msg, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'split' must be a string",
                    exec_ctx,
                )
            )

        return RTResult().failure(RTError(self.pos_start, self.pos_end, msg, exec_ctx))

    execute_error.arg_names = ["message"]

    def execute_split(self, exec_ctx):
        value = exec_ctx.symbol_table.get("string")
        sep = exec_ctx.symbol_table.get("sep")

        if not isinstance(value, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument for 'split' must be a string",
                    exec_ctx,
                )
            )

        if not isinstance(sep, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    "Second argument for 'split' must be a string",
                    exec_ctx,
                )
            )

        return RTResult().success(
            List(
                [
                    String(string)
                    for string in value.value.split(
                        sep.value if len(sep.value) > 0 else " "
                    )
                ]
            )
        )

    execute_split.arg_names = ["string", "sep"]


#######################################
# SETUP VARIABLE FOR ALL BUILT IN FUNCTION
#######################################

# BuiltInFunction.print = BuiltInFunction("print")
# now do this for all the function that starts with execute in BuiltInFunction
for func in [attr for attr in dir(BuiltInFunction) if attr.startswith("execute_")]:
    # get only the part after execute_
    func_name = func[8:]
    setattr(BuiltInFunction, func_name, eval(f"BuiltInFunction('{func_name}')"))
    BUILTIN_FUNCTIONS.append(func_name)


#######################
# Interpreter
#######################
class Interpreter:
    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")

    ###################################

    def visit_NumberNode(self, node, context: Context):
        return RTResult().success(
            Number(node.tok.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_StringNode(self, node, context: Context):
        return RTResult().success(
            String(node.tok.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_ListNode(self, node, context: Context):
        res = RTResult()
        elements = []

        for element_node in node.element_nodes:
            elements.append(res.register(self.visit(element_node, context)))
            if res.should_return():
                return res

        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_VarAccessNode(self, node, context: Context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = context.symbol_table.get(var_name)

        if value is None:
            value = context.private_symbol_table.get(var_name)
            if value is None:
                return res.failure(
                    RTError(
                        node.pos_start,
                        node.pos_end,
                        f"'{var_name}' is not defined",
                        context,
                    )
                )

        value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(value)

    def visit_VarAssignNode(self, node, context: Context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = res.register(self.visit(node.value_node, context))
        if res.should_return():
            return res

        context.symbol_table.set(var_name, value)
        context.private_symbol_table.set(var_name, value)
        return res.success(value)

    def visit_BinOpNode(self, node, context):
        res = RTResult()
        left = res.register(self.visit(node.left_node, context))
        if res.should_return():
            return res
        right = res.register(self.visit(node.right_node, context))
        if res.should_return():
            return res

        if node.op_tok.type == TT_PLUS:
            result, error = left.added_to(right)
        elif node.op_tok.type == TT_MINUS:
            result, error = left.subbed_by(right)
        elif node.op_tok.type == TT_MUL:
            result, error = left.multed_by(right)
        elif node.op_tok.type == TT_DIV:
            result, error = left.dived_by(right)
        elif node.op_tok.type == TT_POW:
            result, error = left.powed_by(right)
        elif node.op_tok.type == TT_MOD:
            result, error = left.moduled_by(right)
        elif node.op_tok.type == TT_EE:
            result, error = left.get_comparison_eq(right)
        elif node.op_tok.type == TT_NE:
            result, error = left.get_comparison_ne(right)
        elif node.op_tok.type == TT_LT:
            result, error = left.get_comparison_lt(right)
        elif node.op_tok.type == TT_DOT:
            result, error = left.dotted_by(right)
        elif node.op_tok.type == TT_GT:
            result, error = left.get_comparison_gt(right)
        elif node.op_tok.type == TT_LTE:
            result, error = left.get_comparison_lte(right)
        elif node.op_tok.type == TT_GTE:
            result, error = left.get_comparison_gte(right)
        elif node.op_tok.matches(TT_KEYWORD, "and"):
            result, error = left.anded_by(right)
        elif node.op_tok.matches(TT_KEYWORD, "or"):
            result, error = left.ored_by(right)

        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_UnaryOpNode(self, node, context):
        res = RTResult()
        number = res.register(self.visit(node.node, context))
        if res.should_return():
            return res

        error = None

        if node.op_tok.type == TT_MINUS:
            number, error = number.multed_by(Number(-1))
        elif node.op_tok.matches(TT_KEYWORD, "not"):
            number, error = number.notted()

        if error:
            return res.failure(error)
        else:
            return res.success(number.set_pos(node.pos_start, node.pos_end))

    def visit_IfNode(self, node, context):
        res = RTResult()

        for condition, expr, should_return_null in node.cases:
            condition_value = res.register(self.visit(condition, context))
            if res.should_return():
                return res

            if condition_value.is_true():
                expr_value = res.register(self.visit(expr, context))
                if res.should_return():
                    return res
                return res.success(Null.null if should_return_null else expr_value)

        if node.else_case:
            expr, should_return_null = node.else_case
            expr_value = res.register(self.visit(expr, context))
            if res.should_return():
                return res
            return res.success(Null.null if should_return_null else expr_value)

        return res.success(Null.null)

    def visit_ForNode(self, node, context):
        res = RTResult()
        elements = []

        start_value = res.register(self.visit(node.start_value_node, context))
        if res.should_return():
            return res

        end_value = res.register(self.visit(node.end_value_node, context))
        if res.should_return():
            return res

        if node.step_value_node:
            step_value = res.register(self.visit(node.step_value_node, context))
            if res.should_return():
                return res
        else:
            step_value = Number(1)

        i = start_value.value

        if step_value.value >= 0:

            def condition():
                return i < end_value.value

        else:

            def condition():
                return i > end_value.value

        while condition():
            context.symbol_table.set(node.var_name_tok.value, Number(i))
            i += step_value.value

            value = res.register(self.visit(node.body_node, context))
            if (
                res.should_return()
                and res.loop_should_continue == False
                and res.loop_should_break == False
            ):
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
            Null.null
            if node.should_return_null
            else List(elements)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_WhileNode(self, node, context):
        res = RTResult()
        elements = []

        while True:
            condition = res.register(self.visit(node.condition_node, context))
            if res.should_return():
                return res

            if not condition.is_true():
                break

            value = res.register(self.visit(node.body_node, context))
            if (
                res.should_return()
                and res.loop_should_continue == False
                and res.loop_should_break == False
            ):
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
            Null.null
            if node.should_return_null
            else List(elements)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_FuncDefNode(self, node, context):
        res = RTResult()

        func_name = node.var_name_tok.value if node.var_name_tok else None
        body_node = node.body_node
        arg_names = [arg_name.value for arg_name in node.arg_name_toks]
        func_value = (
            Function(func_name, body_node, arg_names, node.should_auto_return)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

        if node.var_name_tok:
            context.symbol_table.set(func_name, func_value)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        res = RTResult()
        args = []

        value_to_call = res.register(self.visit(node.node_to_call, context))
        if res.should_return():
            return res
        value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)

        for arg_node in node.arg_nodes:
            args.append(res.register(self.visit(arg_node, context)))
            if res.should_return():
                return res

        return_value = res.register(value_to_call.execute(args))
        if res.should_return():
            return res
        return_value = (
            return_value.copy()
            .set_pos(node.pos_start, node.pos_end)
            .set_context(context)
        )

        return res.success(return_value)

    def visit_ReturnNode(self, node, context):
        res = RTResult()

        if node.node_to_return:
            value = res.register(self.visit(node.node_to_return, context))
            if res.should_return():
                return res
        else:
            value = Null.null

        return res.success_return(value)

    def visit_ThinkNode(self, node, context):
        res = RTResult()

        if node.node_to_think:
            value = res.register(self.visit(node.node_to_think, context))
            if res.should_return():
                return res
        else:
            value = Null.null

        gen_code = generate_code(value)

        return res.success(gen_code)

    def visit_ContinueNode(self, node, context):
        return RTResult().success_continue()

    def visit_BreakNode(self, node, context):
        return RTResult().success_break()

    def visit_ImportNode(self, node: ImportNode, context: Context):
        res = RTResult()
        path = node.file_path

        if not os.path.isfile(path):
            tmp_path = os.path.join(STD_PATH, node.file_path)
            if os.path.isfile(tmp_path):
                path = os.path.join(STD_PATH, node.file_path)
            else:
                return res.failure(
                    RTError(
                        node.pos_start,
                        node.pos_end,
                        f"No module named {tmp_path}",
                        context,
                    )
                )

        result, err = import_module(path, self, context)
        if err:
            if isinstance(err, Error):
                return res.failure(err)
            return res.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    err.error.details,
                    context,
                )
            )

        return res.success(result)


#######################################
# SETUP GLOBAL VARIABLES FOR PRE BUILT FUNCTIONS / VARIABLES
#######################################


global_symbol_table.set("null", Number.null)
global_symbol_table.set("false", Number.false)
global_symbol_table.set("true", Number.true)
global_symbol_table.set("list", String("<list>"))
global_symbol_table.set("str", String("<str>"))
global_symbol_table.set("int", String("<int>"))
global_symbol_table.set("float", String("<float>"))
global_symbol_table.set("function", String("<function>"))
global_symbol_table.set("Run", BuiltInFunction.run)

# load all builtin function to global symbol table
for func in BUILTIN_FUNCTIONS:
    global_symbol_table.set(func, getattr(BuiltInFunction, func))

private_symbol_table = SymbolTable()
private_symbol_table.set("is_main", Number(0))


#######################################
# RUN
#######################################


def run(fn, text):
    # Generate tokens
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error

    result = None
    # Generate AST
    context = None

    try:
        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return None, ast.error

        # Run program
        interpreter = Interpreter()
        context = Context(f"<{fn}>")
        context.symbol_table = global_symbol_table
        context.private_symbol_table = private_symbol_table
        context.private_symbol_table.set("is_main", Number(1))
        result = interpreter.visit(ast.node, context)
        result.value = "" if str(result.value) == "null" else result.value
        return result.value, result.error
    except KeyboardInterrupt:
        err = KeyboardInterruptError(
            position_start, position_end, "Execution interrupted"
        )
        return None, err
