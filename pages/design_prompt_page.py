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
    st.header("Design Prompt")

    if "test_cases" not in st.session_state:
        st.session_state.test_cases = []

    if "intermediate_prompts" not in st.session_state:
        st.session_state.intermediate_prompts = []

    if "current_test_results" not in st.session_state:
        st.session_state.current_test_results = []

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Task Description
    st.subheader("Task Description")
    task_description = st.text_area(
        "Describe what you want to achieve with this prompt:",
        help="Provide a clear description of the task this prompt should accomplish",
    )

    # Test case input section
    st.subheader("Test Cases")

    # Display existing test cases
    for i, test_case in enumerate(st.session_state.test_cases):
        with st.expander(f"Test Case {i+1}"):
            updated_input = st.text_area(
                "Input (JSON)", value=test_case.input_json, key=f"test_input_{i}"
            )
            updated_output = st.text_area(
                "Expected Output", value=test_case.expected_output, key=f"expected_{i}"
            )

            # Update test case if changed
            if (
                updated_input != test_case.input_json
                or updated_output != test_case.expected_output
            ):
                try:
                    # Validate JSON
                    json.loads(updated_input)
                    st.session_state.test_cases[i] = TestCase(
                        input_json=updated_input, expected_output=updated_output
                    )
                except json.JSONDecodeError:
                    st.error("Invalid JSON format in input")

            if st.button("Delete", key=f"delete_{i}"):
                st.session_state.test_cases.pop(i)
                st.rerun()

    # Add new test case
    with st.expander("Add New Test Case"):
        input_json = st.text_area("Input (JSON)")
        expected_output = st.text_area("Expected Output")

        if st.button("Add Test Case"):
            try:
                # Validate JSON
                json.loads(input_json)

                new_test_case = TestCase(
                    input_json=input_json, expected_output=expected_output
                )
                st.session_state.test_cases.append(new_test_case)
                st.success("Test case added successfully!")
                st.rerun()
            except json.JSONDecodeError:
                st.error("Invalid JSON format in input")

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
                with st.expander(f"Iteration {i+1}"):
                    st.markdown("**Suggested Prompt:**")
                    st.code(prompt)
                    st.markdown("**Test Case Results:**")
                    for j, score in enumerate(test_results):
                        st.write(f"Test Case {j+1}: {test_results["score"]:.2f}")
                        st.write(f"Expected: {test_results["expected"]}")
                        st.write(f"Actual: {test_results["actual"]}")


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
            "content": """You are an expert prompt engineer. Your task is to design a prompt template that works perfectly for all given test cases.
            You will receive a task description and test cases, and you should create a prompt template that achieves the desired results.""",
        },
        {
            "role": "user",
            "content": f"""Task Description: {task_description}

Please design a prompt template that will work with the following test cases:

{test_cases_str}

Requirements:
1. Use Jinja2 template syntax for variables (e.g. {{variable_name}})
2. The prompt should achieve the described task
3. Generate output exactly matching the expected output format
4. Work consistently across all test cases
5. Include clear instructions and context in the prompt template

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

Provide only the improved prompt template, nothing else.""",
    }
