
import time

import streamlit as st

from pages.create_page import show_create_page
from db_operations import (
    delete_prompt,
    get_all_prompts,
    upvote_prompt,
)

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
                    st.switch_page(st.Page(show_create_page))
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
