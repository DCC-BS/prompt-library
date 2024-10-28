import json
import asyncio
import streamlit as st
from jinja2 import Template

from db_operations import (
    Prompt,
    save_prompt,
    update_prompt,
    get_prompt_versions
)
from utils import (
    validate_variables_with_template,
    get_template_variables,
    test_multiple_models,
)
from config_handler import ConfigHandler

config = ConfigHandler()
MAX_ENDPOINTS = 5


def show_create_page():
    st.header("Create New Prompt")
    _create_section()
    _test_section()


def _create_section():
    editing_prompt = st.session_state.get("editing_prompt")

    if editing_prompt:
        st.info(f"Editing prompt: {editing_prompt.name} (Version {editing_prompt.version})")
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
        help="See Jinja for template guidance: https://jinja.palletsprojects.com/en/stable/templates/#synopsis "
    )

    variables = get_template_variables(st.session_state["creation_template"])

    st.session_state["template_values"] = {}
    default_values = json.loads(editing_prompt.example_values) if editing_prompt else {}
    for var in variables:
        st.session_state["template_values"][var] = st.text_input(
            f"Value for {var}", value=default_values.get(var, "")
        )

    if st.button("Save Prompt"):
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

            prompt = Prompt(
                id=editing_prompt.id if editing_prompt else None,
                name=name,
                author=author,
                template=st.session_state["creation_template"],
                example_values=json.dumps(
                    st.session_state["template_values"], ensure_ascii=False
                ),
                upvotes=editing_prompt.upvotes if editing_prompt else 0,
            )

            prompt = Prompt(
                id=editing_prompt.id if editing_prompt else None,
                name=name,
                author=author,
                template=st.session_state["creation_template"],
                example_values=json.dumps(
                    st.session_state["template_values"], ensure_ascii=False
                ),
                upvotes=editing_prompt.upvotes if editing_prompt else 0, # Version inherit the upvotes
                version=1 if not editing_prompt else None,  # Version will be set in update_prompt
                parent_id=None if not editing_prompt else editing_prompt.id
            )

            if editing_prompt:
                update_prompt(prompt)
                st.success("✅ New version successfully!")
            else:
                save_prompt(prompt)
                st.success("✅ Prompt saved successfully!")

            st.session_state.editing_prompt = None

        except json.JSONDecodeError:
            st.error("❌ Invalid JSON format in example values")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


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
