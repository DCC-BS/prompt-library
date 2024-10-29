import aiohttp
from typing import List, Tuple
import json
import jinja2
import asyncio

async def test_prompt_with_model(url: str, prompt: str, model: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"prompt": prompt, "model": model, "stream": False}) as response:
                result = await response.text()
                response = json.loads(result)
                return response["response"]
        except Exception as e:
            return f"Error: {str(e)}"


async def test_multiple_models(urls: List[str], prompt: str, models: List[str]) -> dict:
    tasks = [test_prompt_with_model(url, prompt, model) for url, model in zip(urls, models)]
    results = await asyncio.gather(*tasks)
    return dict(zip(models, results))

def get_template_variables(template_str: str) -> List[str]:
    """Extract variable names from a Jinja2 template string"""
    env = jinja2.Environment()
    ast = env.parse(template_str)
    variables = set()

    def visit_node(node):
        if isinstance(node, jinja2.nodes.Name):
            variables.add(node.name)
        for child in node.iter_child_nodes():
            visit_node(child)

    visit_node(ast)
    return list(variables)

def validate_variables_with_template(values: dict, template_str: str) -> Tuple[bool, str]:
    if isinstance(values, str):
        values = json.loads(values)
    template_vars = get_template_variables(template_str)
    for template_var in template_vars:
        if template_var not in values.keys() or values[template_var] == '' or values[template_var] is None:
            return False, template_var
    return True, ""


def evaluate_test_case(llm_output: str, expected_output: str) -> bool:
    return llm_output.strip().lower() == expected_output.strip().lower()