import asyncio
import json

import streamlit as st
from jinja2 import Template

from config_handler import ConfigHandler
from db_operations import (
    Prompt,
    TestCase,
    delete_test_case,
    get_prompt_versions,
    get_test_cases,
    save_prompt,
    save_test_case,
    update_prompt,
    update_test_case,
)
from utils import (
    get_template_variables,
    test_multiple_models,
    validate_variables_with_template,
)

config = ConfigHandler()
MAX_ENDPOINTS = 5


def show_create_page():
    with st.expander("ℹ️ How to use this page", expanded=False):
        st.markdown("""
        **Create/Edit Prompt Page Instructions:**
        1. Fill in prompt details:
           - Name and author
           - Template using Jinja2 syntax {{variable}}
           - Example values for variables
        2. Add test cases:
           - Input values for the Jinja2 template in JSON format
           - Expected output
        3. Test your prompt:
           - Select LLM endpoints
           - View rendered prompt
           - Compare responses
        4. Save to create new prompt or version
        """)

    st.header("Create New Prompt")
    _create_section()
    _test_section()


def _create_section():
    editing_prompt = st.session_state.get("editing_prompt")

    if editing_prompt:
        st.info(
            f"Editing prompt: {editing_prompt.name} (Version {editing_prompt.version})"
        )
        versions = get_prompt_versions(editing_prompt.id)
        if len(versions) > 1:
            st.info(f"This prompt has {len(versions)} versions")

    name = st.text_input(
        "Prompt Name", value=editing_prompt.name if editing_prompt else ""
    )
    author = st.text_input(
        "Author", value=editing_prompt.author if editing_prompt else ""
    )
    st.session_state["creation_template"] = st.text_area(
        "Prompt Template (Use {{variable}} for template variables)",
        value=editing_prompt.template if editing_prompt else "",
        help="See Jinja for template guidance: https://jinja.palletsprojects.com/en/stable/templates/#synopsis ",
    )

    variables = get_template_variables(st.session_state["creation_template"])

    st.session_state["template_values"] = {}
    default_values = json.loads(editing_prompt.example_values) if editing_prompt else {}
    for var in variables:
        st.session_state["template_values"][var] = st.text_input(
            f"Value for {var}", value=default_values.get(var, "")
        )

    st.divider()
    st.subheader("Test Cases")

    if "test_cases" not in st.session_state:
        st.session_state.test_cases = []

    # Load existing test cases if editing
    if editing_prompt and not st.session_state.test_cases:
        p_id = editing_prompt.parent_id if editing_prompt.parent_id else editing_prompt.id
        st.session_state.test_cases = get_test_cases(p_id)

    # Display existing test cases
    for i, test_case in enumerate(st.session_state.test_cases):
        with st.expander(f"Test Case {i+1}"):
            st.text_area(
                "Input Variables (JSON)",
                value=test_case.input_values,
                key=f"test_inputs_{i}",
            )
            st.text_area(
                "Expected Output", value=test_case.expected_output, key=f"expected_{i}"
            )
            if st.button("Delete Test Case", key=f"delete_test_{i}"):
                if test_case.id:  # If it's an existing test case
                    delete_test_case(test_case.id)
                st.session_state.test_cases.pop(i)
                st.rerun()

    # Add new test case
    st.subheader("Add Test Case")
    if st.button("Add Test Case"):
        test_case = TestCase(
            id=None,
            prompt_id=editing_prompt.id if editing_prompt else None,
            input_values=json.dumps(st.session_state["template_values"]),
            expected_output="",
        )
        st.session_state.test_cases.append(test_case)
        st.rerun()

    if st.button("Save Prompt"):
        _save_prompt_and_test(editing_prompt, name, author)


def _save_prompt_and_test(editing_prompt, name, author):
    try:
        # Validate Jinja template
        Template(st.session_state["creation_template"])

        # Validate example values for each template value:
        is_valid, missing = validate_variables_with_template(
            st.session_state["template_values"],
            st.session_state["creation_template"],
        )
        if not is_valid:
            st.error(f"❌ Missing variable {missing} in input.")
            return

        prompt = _save_or_update_prompt(editing_prompt, name, author)
        _save_or_update_test_cases(prompt)

        st.session_state.test_cases = []
        st.session_state.editing_prompt = None
    except json.JSONDecodeError:
        st.error("❌ Invalid JSON format in example values")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        raise e


def _save_or_update_prompt(editing_prompt, name, author):
    prompt = Prompt(
        id=None,
        name=name,
        author=author,
        template=st.session_state["creation_template"],
        example_values=json.dumps(
            st.session_state["template_values"], ensure_ascii=False
        ),
        upvotes=editing_prompt.upvotes
        if editing_prompt
        else 0,  # Version inherit the upvotes
        version=1
        if not editing_prompt
        else None,  # Version will be set in update_prompt
        parent_id=None if not editing_prompt else editing_prompt.id,
    )

    if editing_prompt:
        if prompt != editing_prompt:
            prompt_id = update_prompt(prompt)
            prompt.id = prompt_id
            st.success("✅ New version successfully!")
    else:
        prompt_id = save_prompt(prompt)
        prompt.id = prompt_id
        st.success("✅ Prompt saved successfully!")
    return prompt


def _save_or_update_test_cases(prompt):
    for idx, test_case in enumerate(st.session_state.test_cases):
        test_case.prompt_id = prompt.parent_id if prompt.parent_id else prompt.id
        test_case.expected_output = st.session_state.get(f"expected_{idx}", "")
        test_case.input_values = st.session_state.get(f"test_inputs_{idx}", "")
        print(prompt)
        print(test_case)
        if test_case.id:
            update_test_case(test_case)
            st.success("✅ Updated test case successfully!")
        else:
            save_test_case(test_case)
            st.success("✅ Added new test case successfully!")


def _test_section():
    if template := st.session_state["creation_template"]:
        st.divider()
        st.subheader("Test Prompt")

        try:
            available_endpoints = config.endpoints

            if not available_endpoints:
                st.error(
                    "❌ No LLM endpoints configured. Please check your config.yaml file."
                )
            else:
                variables = get_template_variables(
                    st.session_state["creation_template"]
                )
                values = {}
                for var in variables:
                    values[var] = st.session_state["template_values"][var]

                # Endpoint selection
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

                if st.button("🧪 Test Prompt") and selected_endpoints:
                    try:
                        is_valid, missing = validate_variables_with_template(
                            values, template
                        )
                        if not is_valid:
                            st.error(f"❌ Missing value {missing} in input.")
                            return

                        template_obj = Template(template)
                        rendered_prompt = template_obj.render(**values)

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
                        for endpoint, response in zip(
                            selected_endpoints, results.values()
                        ):
                            st.write(f"**{endpoint.name}:**")
                            st.write(response)
                            st.markdown("---")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        except Exception as e:
            st.error(f"❌ Error in test prompt section: {str(e)}")
