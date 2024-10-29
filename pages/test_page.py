import asyncio
import json

import clipboard
import streamlit as st
from jinja2 import Template

from config_handler import ConfigHandler
from db_operations import get_latest_versions, get_prompt_versions, get_test_cases
from utils import (
    get_template_variables,
    test_multiple_models,
    validate_variables_with_template,
    evaluate_test_case
)

config = ConfigHandler()
MAX_ENDPOINTS = 5


def show_test_page():
    st.header("Test Prompts")

    available_endpoints = config.endpoints

    if not available_endpoints:
        st.error("❌ No LLM endpoints configured. Please check your config.yaml file.")
        return

    prompts = get_latest_versions()
    selected_prompt = st.selectbox(
        "Select a prompt to test", 
        options=prompts, 
        format_func=lambda x: f"{x.name} (v{x.version})"
    )

    if selected_prompt:
        p_id = selected_prompt.parent_id if selected_prompt.parent_id else selected_prompt.id
        test_cases = get_test_cases(p_id)

        versions = get_prompt_versions(selected_prompt.id)

        version_options = [f"Version {v.version} ({v.created_at})" for v in versions]
        selected_version_idx = st.selectbox(
            "Select version:",
            range(len(version_options)),
            format_func=lambda x: version_options[x],
            key=f"version_select_{selected_prompt.id}"
        )
        
        selected_prompt = versions[selected_version_idx]

        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader("Template")
        with col2:
            if st.button("📑 Copy Prompt"):
                clipboard.copy(selected_prompt.template)
                st.success("✅ Copied to clipboard!")
        st.markdown(selected_prompt.template)

        variables = get_template_variables(selected_prompt.template)
        example_variables_input = json.loads(selected_prompt.example_values)

        values = {}
        for var in variables:
            values[var] = st.text_input(
                f"Value for {var}", value=example_variables_input[var]
            )

        st.subheader("Select LLM Endpoints")
        selected_endpoints = []

        selected_names = st.multiselect(
            "Choose one or more endpoints to test with:",
            options=[endpoint.name for endpoint in available_endpoints],
            max_selections=MAX_ENDPOINTS,
            help="Select the LLM endpoints you want to test your prompt with",
        )

        selected_endpoints = [
            endpoint
            for endpoint in available_endpoints
            if endpoint.name in selected_names
        ]

        if len(selected_endpoints) > MAX_ENDPOINTS:
            st.warning(f"You can select a maximum of {MAX_ENDPOINTS} endpoints.")
            selected_endpoints = selected_endpoints[:MAX_ENDPOINTS]

        if selected_endpoints:
            st.subheader("Selected Endpoints:")
            for endpoint in selected_endpoints:
                with st.expander(f"{endpoint.name}"):
                    st.write(f"**URL:** {endpoint.url}")
                    st.write(f"**Description:** {endpoint.description}")

        if st.button("🚀 Test Prompt") and selected_endpoints:
            try:
                is_valid, missing = validate_variables_with_template(
                    values, selected_prompt.template
                )
                if not is_valid:
                    st.error(f"❌ Missing value {missing} in input.")
                    return

                # Render template with provided values
                template = Template(selected_prompt.template)
                rendered_prompt = template.render(**values)

                st.subheader("Rendered Prompt")
                st.markdown(rendered_prompt)

                results = asyncio.run(
                    test_multiple_models(
                        [endpoint.url for endpoint in selected_endpoints],
                        rendered_prompt,
                        [endpoint.model for endpoint in selected_endpoints],
                    )
                )

                st.subheader("Results")
                for endpoint, response in zip(selected_endpoints, results.values()):
                    st.write(f"**{endpoint.name}:**")
                    st.write(response)
                    st.markdown("---")

                if test_cases:
                    st.subheader("Test Case Results")
                    for i, test_case in enumerate(test_cases):
                        st.write(f"**Test Case {i+1}:**")
                        input_values = json.loads(test_case.input_values)
                        template = Template(selected_prompt.template)
                        test_prompt = template.render(**input_values)
                        
                        test_results = asyncio.run(
                            test_multiple_models(
                                [endpoint.url for endpoint in selected_endpoints],
                                test_prompt,
                                [endpoint.model for endpoint in selected_endpoints],
                            )
                        )
                        
                        for endpoint, response in zip(selected_endpoints, test_results.values()):
                            passed = evaluate_test_case(response, test_case.expected_output)
                            status = "✅ PASSED" if passed else "❌ FAILED"
                            
                            with st.expander(f"{endpoint.name} - {status}"):
                                st.write("**Input:**")
                                st.json(input_values)
                                st.write("**Expected Output:**")
                                st.write(test_case.expected_output)
                                st.write("**Actual Output:**")
                                st.write(response)

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
