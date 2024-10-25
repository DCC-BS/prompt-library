import asyncio
import json

import streamlit as st
from jinja2 import Template

from config_handler import ConfigHandler
from db_operations import get_all_prompts
from utils import (
    get_template_variables,
    test_multiple_models,
    validate_variables_with_template,
)

config = ConfigHandler()
MAX_ENDPOINTS = 3


def show_test_page():
    st.header("Test Prompts")

    available_endpoints = config.endpoints

    if not available_endpoints:
        st.error("No LLM endpoints configured. Please check your config.yaml file.")
        return

    prompts = get_all_prompts()
    selected_prompt = st.selectbox(
        "Select a prompt to test", options=prompts, format_func=lambda x: x.name
    )

    if selected_prompt:
        st.subheader("Template")
        st.text(selected_prompt.template)

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

        if st.button("Test Prompt") and selected_endpoints:
            try:
                is_valid, missing = validate_variables_with_template(
                    values, selected_prompt.template
                )
                if not is_valid:
                    st.error(f"Missing value {missing} in input.")
                    return

                # Render template with provided values
                template = Template(selected_prompt.template)
                rendered_prompt = template.render(**values)

                st.subheader("Rendered Prompt")
                st.text(rendered_prompt)

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

            except Exception as e:
                st.error(f"Error: {str(e)}")
