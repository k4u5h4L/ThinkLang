import src
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re

import warnings

warnings.filterwarnings("ignore")

os.environ["TRANSFORMERS_VERBOSITY"] = "error"

print("Importing the brains behind this stupid language (Deepseek lol)...")
tokenizer = AutoTokenizer.from_pretrained(
    "deepseek-ai/deepseek-coder-1.3b-instruct", trust_remote_code=True
)
model = AutoModelForCausalLM.from_pretrained(
    "deepseek-ai/deepseek-coder-1.3b-instruct",
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
)

path = os.getcwd() + "/examples"
os.environ["HF_HOME"] = os.getcwd() + "/cache/models"


def gather_prompt(prompt: str) -> str:
    training_codes = ""
    sample_codes = [f"{path}/{f}" for f in os.listdir(path=path)]

    # map them into a single string and feed that into the model as context
    for code_loc in sample_codes:
        with open(code_loc) as f:
            training_codes += f.read()
            training_codes += "\n"

    instruct_prompt = f"""You are a software developer writing code in a new language. The language syntax is shown below:
        {training_codes}

        You are to code in this langauge using this syntax. Write just the source code without any explanation.
        
        Prompt: {prompt}"""

    return instruct_prompt


def generate_respose(prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    ).to(model.device)
    # tokenizer.eos_token_id is the id of <|EOT|> token
    outputs = model.generate(
        inputs,
        max_new_tokens=512,
        do_sample=False,
        top_k=50,
        top_p=0.95,
        num_return_sequences=1,
        eos_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(outputs[0][len(inputs[0]) :], skip_special_tokens=True)


def extract_triple_backtick_blocks(text):
    # This regex matches content between triple backticks, including multiline content
    pattern = r"```(.*?)```"
    # re.DOTALL allows '.' to match newline characters too
    return re.findall(pattern, text, re.DOTALL)[0]


def clean_response(response: str) -> str:
    print(extract_triple_backtick_blocks(response))


def generate_code(initial_prompt: str) -> str:
    prompt = gather_prompt(prompt=initial_prompt)
    response = generate_respose(prompt=prompt)
    response = clean_response(response)
    src.interpreter.run("<stdin>", response)
    return initial_prompt

    # ask it to generate new code based on the syntax
