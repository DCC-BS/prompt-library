import json

import streamlit as st
from jinja2 import Template

from db_operations import (
    Prompt,
    save_prompt,
    update_prompt,
)
from utils import validate_variables_with_template


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
            is_valid, missing = validate_variables_with_template(
                example_values, template
            )
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
