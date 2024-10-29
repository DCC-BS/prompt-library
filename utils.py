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

async def compare_strings_with_llm_judge(
    llm_output: str,
    expected_output: str,
    original_instruction: str,
    test_prompt_func,
    url: str,
    model: str
) -> float:
    judge_prompt = f"""You are an expert judge evaluating if an LLM's response correctly follows the given instructions and matches the expected output.

    ORIGINAL TASK INSTRUCTIONS:
    {original_instruction}

    EXPECTED OUTPUT:
    {expected_output}

    LLM'S RESPONSE:
    {llm_output}

    Instructions for evaluation:
    1. First, carefully analyze if the LLM's response follows the original task instructions correctly
    2. Then, compare the semantic similarity between the LLM's response and the expected output
    3. Consider these aspects in your evaluation:
       - Does the response correctly address all requirements from the original instructions?
       - Is the format and structure correct?
       - Is the semantic meaning equivalent?
       - Are there any missing or extra elements?
    
    Scoring criteria:
    - 1.0: Perfect match in both following instructions and matching expected output
    - 0.8-0.9: Minor differences but maintains core meaning and follows instructions
    - 0.5-0.7: Partially correct but has notable omissions or differences
    - 0.2-0.4: Major differences or missing key elements
    - 0.0-0.1: Completely incorrect or fails to follow instructions

    Provide your score as a single number between 0.0 and 1.0.
    Response format: Only return the numerical score, nothing else.

    Score:"""
    
    try:
        score_response = await test_prompt_func(url, judge_prompt, model)
        
        score = float(score_response.strip().replace('\n', ''))
        
        score = max(0.0, min(1.0, score))
        
        return score
    except ValueError:
        return 0.0
