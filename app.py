import asyncio
import json
import time
from typing import List, Tuple

import aiohttp
import jinja2
import streamlit as st
from jinja2 import Template

from config_handler import ConfigHandler
from db_operations import (
    Prompt,
    delete_prompt,
    get_all_prompts,
    init_db,
    save_prompt,
    update_prompt,
    upvote_prompt,
)

config = ConfigHandler()
MAX_ENDPOINTS = 5


async def test_prompt_with_model(url: str, prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"prompt": prompt}) as response:
                result = await response.json()
                return result.get("response", "Error: No response received")
        except Exception as e:
            return f"Error: {str(e)}"


async def test_multiple_models(urls: List[str], prompt: str) -> dict:
    tasks = [test_prompt_with_model(url, prompt) for url in urls]
    results = await asyncio.gather(*tasks)
    return dict(zip(urls, results))


def main():
    st.title("Prompt Library")

    init_db()

    if "page" not in st.session_state:
        st.session_state.page = "Browse Prompts"

    st.session_state.page = st.sidebar.selectbox(
        "Choose a page",
        ["Browse Prompts", "Create New Prompt", "Test Prompts"],
        index=["Browse Prompts", "Create New Prompt", "Test Prompts"].index(
            st.session_state.page
        ),
    )

    if st.session_state.page == "Browse Prompts":
        show_browse_page()
    elif st.session_state.page == "Create New Prompt":
        show_create_page()
    elif st.session_state.page == "Test Prompts":
        show_test_page()


def show_browse_page():
    st.header("Browse Prompts")
    prompts = get_all_prompts()

    if "delete_confirmation" not in st.session_state:
        st.session_state.delete_confirmation = None

    for prompt in prompts:
        with st.expander(f"{prompt.name} by {prompt.author} (👍 {prompt.upvotes})"):
            md_text = (
                "## Template\n"
                f"{prompt.template}\n"
                "## Example Values\n"
                f"`{prompt.example_values}`"
            )
            st.markdown(md_text)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Upvote", key=f"upvote_{prompt.id}"):
                    upvote_prompt(prompt.id)
                    st.success("Upvote recorded!")
            with col2:
                if st.button("Edit", key=f"edit_{prompt.id}"):
                    st.session_state.editing_prompt = prompt
                    st.session_state.page = "Create New Prompt"
                    st.rerun()
            with col3:
                if st.session_state.delete_confirmation == prompt.id:
                    if st.button("Confirm Delete", key=f"confirm_delete_{prompt.id}"):
                        delete_prompt(prompt.id)
                        st.session_state.delete_confirmation = None
                        st.success("Prompt deleted successfully!")
                        time.sleep(1)
                        st.rerun()
                    if st.button("Cancel", key=f"cancel_delete_{prompt.id}"):
                        st.session_state.delete_confirmation = None
                        st.rerun()
                else:
                    if st.button("Delete", key=f"delete_{prompt.id}"):
                        st.session_state.delete_confirmation = prompt.id
                        st.rerun()


def show_create_page():
    st.header("Create New Prompt")

    editing_prompt = st.session_state.get("editing_prompt")

    name = st.text_input(
        "Prompt Name", value=editing_prompt.name if editing_prompt else ""
    )
    author = st.text_input(
        "Author", value=editing_prompt.author if editing_prompt else ""
    )
    template = st.text_area(
        "Prompt Template (Use {{variable}} for template variables)",
        value=editing_prompt.template if editing_prompt else "",
    )
    example_values = st.text_area(
        "Example Values (JSON format)",
        value=editing_prompt.example_values if editing_prompt else "{}",
    )

    if st.button("Save Prompt"):
        try:
            # Validate JSON format for example values
            json.loads(example_values)

            # Validate Jinja template
            Template(template)

            # Validate example values for each template value:
            is_valid, missing = validate_variables_with_template(example_values, template)
            if not is_valid:
                st.error(f"Missing variable {missing} in input.")
                return

            prompt = Prompt(
                id=editing_prompt.id if editing_prompt else None,
                name=name,
                author=author,
                template=template,
                example_values=example_values,
                upvotes=editing_prompt.upvotes if editing_prompt else 0,
            )

            if editing_prompt:
                update_prompt(prompt)
                st.success("Prompt updated successfully!")
            else:
                save_prompt(prompt)
                st.success("Prompt saved successfully!")

            st.session_state.editing_prompt = None

        except json.JSONDecodeError:
            st.error("Invalid JSON format in example values")
        except Exception as e:
            st.error(f"Error: {str(e)}")


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
            values[var] = st.text_input(f"Value for {var}", value=example_variables_input[var])

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
                is_valid, missing = validate_variables_with_template(values, selected_prompt.template)
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
                    )
                )

                st.subheader("Results")
                for endpoint, response in zip(selected_endpoints, results.values()):
                    st.write(f"**{endpoint.name}:**")
                    st.write(response)
                    st.markdown("---")

            except Exception as e:
                st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
