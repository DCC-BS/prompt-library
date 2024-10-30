import asyncio
import json
from dataclasses import dataclass
from typing import List

import streamlit as st
from jinja2 import Template

from utils import (
    test_prompt_with_model,
    compare_strings_with_llm_judge,
    test_prompt_with_chat_model,
)
from config_handler import ConfigHandler

config = ConfigHandler()
MAX_ITERATIONS = 10


@dataclass
class TestCase:
    input_json: str
    expected_output: str


def show_design_prompt_page():
    with st.expander("ℹ️ How to use this page", expanded=False):
        st.markdown("""
        **Design Prompt Page Instructions:**
        1. Upload a JSON file containing:
           - Task description
           - Test cases with input/expected output pairs
        2. Select LLM endpoints for:
           - Prompt design (generates prompts)
           - Testing (evaluates prompts)
        3. The system will:
           - Generate prompt templates iteratively
           - Test against provided test cases
           - Use LLM as judge to score outputs
           - Show detailed results and improvements
        
        Download the example JSON to see the required format.
        """)
        
    st.header("Design Prompt")

    if "test_cases" not in st.session_state:
        st.session_state.test_cases = []

    if "intermediate_prompts" not in st.session_state:
        st.session_state.intermediate_prompts = []

    if "current_test_results" not in st.session_state:
        st.session_state.current_test_results = []

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("Upload Task Description and Test Cases")

    # Add download link for example JSON
    example_json = {
        "task_description": "Convert the given number into its roman numeral representation",
        "test_cases": [
            {"input_json": '{"number": 9}', "expected_output": "IX"},
            {"input_json": '{"number": 58}', "expected_output": "LVIII"},
        ],
    }
    st.download_button(
        "Download Example JSON",
        data=json.dumps(example_json, indent=4),
        file_name="example_input.json",
        mime="application/json",
    )

    uploaded_file = st.file_uploader(
        "Upload JSON file with task description and test cases",
        type=["json"],
        help="Upload a JSON file containing task description and test cases. Click 'Download Example JSON' to see the required format.",
    )

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            task_description = data.get("task_description")
            test_cases_data = data.get("test_cases", [])

            # Validate the uploaded JSON structure
            if not task_description:
                st.error("Task description is missing in the JSON file")
                return

            if not test_cases_data:
                st.error("No test cases found in the JSON file")
                return

            # Convert the test cases data to TestCase objects
            st.session_state.test_cases = [
                TestCase(
                    input_json=test_case["input_json"],
                    expected_output=test_case["expected_output"],
                )
                for test_case in test_cases_data
            ]

            # Display the loaded task description
            st.subheader("Task Description")
            st.write(task_description)

            # Display loaded test cases
            st.subheader("Loaded Test Cases")
            for i, test_case in enumerate(st.session_state.test_cases):
                with st.expander(f"Test Case {i+1}"):
                    st.text_area(
                        "Input (JSON)",
                        value=test_case.input_json,
                        key=f"test_input_{i}",
                        disabled=True,
                    )
                    st.text_area(
                        "Expected Output",
                        value=test_case.expected_output,
                        key=f"expected_{i}",
                        disabled=True,
                    )

        except json.JSONDecodeError:
            st.error("Invalid JSON file format")
            return
        except KeyError as e:
            st.error(f"Missing required field in JSON: {str(e)}")
            return
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            return

    # Prompt design section
    if st.session_state.test_cases and task_description:
        st.subheader("Design Prompt")

        available_endpoints = config.endpoints
        if not available_endpoints:
            st.error("No LLM endpoints configured. Please check your config.yaml file.")
            return

        col1, col2 = st.columns(2)
        with col1:
            design_endpoint = st.selectbox(
                "Choose LLM endpoint for prompt design:",
                options=available_endpoints,
                format_func=lambda x: x.name,
                key="design_endpoint",
            )
        with col2:
            test_endpoint = st.selectbox(
                "Choose LLM endpoint for testing:",
                options=available_endpoints,
                format_func=lambda x: x.name,
                key="test_endpoint",
            )

        if st.button("Generate Prompt"):
            st.session_state.intermediate_prompts = []
            st.session_state.current_test_results = []
            st.session_state.chat_history = _create_initial_chat_history(
                task_description, st.session_state.test_cases
            )

            progress_container = st.empty()
            with progress_container.container():
                st.write("Starting prompt design process...")

            for iteration in range(MAX_ITERATIONS):
                with progress_container.container():
                    st.write(f"Iteration {iteration + 1}/{MAX_ITERATIONS}")

                    # Get prompt suggestion from LLM using chat endpoint
                    st.write("Generating prompt suggestion...")
                    prompt_response_message = asyncio.run(
                        test_prompt_with_chat_model(
                            design_endpoint.url,
                            st.session_state.chat_history,
                            design_endpoint.model,
                        )
                    )

                    st.session_state.chat_history.append(prompt_response_message)
                    st.session_state.intermediate_prompts.append(
                        prompt_response_message["content"]
                    )

                    st.markdown("**Current Prompt:**")
                    st.code(prompt_response_message["content"])

                    # Test the suggested prompt
                    st.write("Testing prompt against test cases...")
                    scores = []
                    all_perfect = True
                    test_results = []

                    for i, test_case in enumerate(st.session_state.test_cases):
                        try:
                            test_input = json.loads(test_case.input_json)
                            template = Template(prompt_response_message["content"])
                            rendered_prompt = template.render(**test_input)

                            llm_output = asyncio.run(
                                test_prompt_with_model(
                                    test_endpoint.url,
                                    rendered_prompt,
                                    test_endpoint.model,
                                )
                            )

                            score = asyncio.run(
                                compare_strings_with_llm_judge(
                                    llm_output=llm_output,
                                    expected_output=test_case.expected_output,
                                    original_instruction=rendered_prompt,
                                    test_prompt_func=test_prompt_with_model,
                                    url=test_endpoint.url,
                                    model=test_endpoint.model,
                                )
                            )
                            scores.append(score)
                            test_results.append(
                                {
                                    "input": test_case.input_json,
                                    "expected": test_case.expected_output,
                                    "actual": llm_output,
                                    "score": score,
                                }
                            )

                            st.write(
                                f"Test Case {i+1} Score: {score:.2f} \n Generated Output: {llm_output} \n Expected Output: {test_case.expected_output}"
                            )

                            if score < 1.0:
                                all_perfect = False

                        except Exception as e:
                            st.error(f"Error testing prompt: {str(e)}")
                            scores.append(0.0)
                            all_perfect = False

                    st.session_state.current_test_results.append(test_results)

                    if all_perfect:
                        st.success("Perfect scores achieved! Stopping iterations.")
                        break

                    # Add feedback message to chat history
                    st.write("Generating feedback for next iteration...")
                    feedback_message = _create_feedback_message(test_results)
                    st.session_state.chat_history.append(feedback_message)

            progress_container.empty()

        # Display results
        if st.session_state.intermediate_prompts:
            st.subheader("Results History")

            for i, (prompt, test_results) in enumerate(
                zip(
                    st.session_state.intermediate_prompts,
                    st.session_state.current_test_results,
                )
            ):
                average_score = sum([result["score"] for result in test_results]) / len(test_results)
                with st.expander(f"Iteration {i+1} - Average Score: {average_score}"):
                    st.markdown("**Suggested Prompt:**")
                    st.code(prompt)
                    st.markdown("**Test Case Results:**")
                    for j, test_result in enumerate(test_results):
                        st.write(f"Test Case {j+1}: {test_result["score"]:.2f}")
                        st.write(f"Expected: {test_result["expected"]}")
                        st.write(f"Actual: {test_result["actual"]}")

            # Reset State
            st.session_state.test_cases = []
            st.session_state.intermediate_prompts = []
            st.session_state.current_test_results = []
            st.session_state.chat_history = []


def _create_initial_chat_history(
    task_description: str, test_cases: List[TestCase]
) -> List[dict]:
    test_cases_str = "\n\n".join(
        [
            f"Test Case {i+1}:\n"
            f"Input: {test_case.input_json}\n"
            f"Expected Output: {test_case.expected_output}"
            for i, test_case in enumerate(test_cases)
        ]
    )

    return [
        {
            "role": "system",
            "content": """You are an expert prompt engineer. Your task is to design a prompt template that works perfectly for all given test cases and is as general as possible to work in scenarios outside of the provided test cases.
            You will receive a task description and test cases, and you should create a prompt template following the Jinja2 template syntax that achieves the desired results. DO NOT include the test cases into the prompt.""",
        },
        {
            "role": "user",
            "content": f"""Task Description: {task_description}

Please design a prompt template that will work with the following test cases:

{test_cases_str}

Requirements:
1. Use Jinja2 template syntax for variables (e.g. {{ variable_name }} )
2. Jinja2 template variables are always surrounded with double curly brackets.
3. The prompt should achieve the described task
4. Generate output exactly matching the expected output format
5. Work consistently across all test cases
6. Include clear instructions and context in the prompt template
7. Do not write any code or instruct the model to do so
8. The designed prompt temlpate should be as general as possible to work outside of the provided test cases in similar scenarios
9. DO NOT include the test cases into the prompt template, if needed come up with other examples outside of the provided test cases

Provide only the prompt template, nothing else.""",
        },
    ]


def _create_feedback_message(test_results: List[dict]) -> dict:
    feedback = "\n\n".join(
        [
            f"Test Case {i+1}:\n"
            f"Input: {result['input']}\n"
            f"Expected: {result['expected']}\n"
            f"Actual: {result['actual']}\n"
            f"Score: {result['score']:.2f}"
            for i, result in enumerate(test_results)
        ]
    )

    return {
        "role": "user",
        "content": f"""Here are the test results for your prompt template:

{feedback}

Please improve the prompt template to achieve perfect scores (1.0) for all test cases.
Focus on:
1. Fixing any mismatches between generated and expected output
2. Making instructions clearer and more specific
3. Ensuring consistent formatting
4. Maintaining the core task requirements
5. Keep the prompt as concise as possible
6. Make sure you use Jinja2 template syntax for variables. Example: If the template variable name is "input", then the template using this variable is {{ input }}
7. Do not include the test cases into the prompt template, if needed come up with other examples outside of the provided test cases.

Provide only the improved prompt template, nothing else.""",
    }
