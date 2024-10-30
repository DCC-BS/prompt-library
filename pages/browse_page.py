
import time

import clipboard
import streamlit as st

from db_operations import (
    delete_prompt,
    upvote_prompt,
    get_prompt_versions,
    get_latest_versions,
)
from pages.create_page import show_create_page


def show_browse_page():
    with st.expander("ℹ️ How to use this page", expanded=False):
        st.markdown("""
        **Browse Prompts Page Instructions:**
        1. Browse through all available prompts in the library
        2. Expand prompts to view details and different versions
        3. Use the version selector to switch between prompt versions
        4. Available actions for each prompt:
           - Upvote (👍) useful prompts
           - Edit (✏️) to create new versions
           - Delete (🗑️) prompts you created
           - Copy (📋) prompt template to clipboard
        """)

    st.header("Browse Prompts")
    prompts = get_latest_versions()

    if "delete_confirmation" not in st.session_state:
        st.session_state.delete_confirmation = None

    for prompt in prompts:
        with st.expander(f"{prompt.name} by {prompt.author} (👍 {prompt.upvotes}) - v{prompt.version}"):
            versions = get_prompt_versions(prompt.id)

            version_options = [f"Version {v.version} ({v.created_at})" for v in versions]
            selected_version_idx = st.selectbox(
                "Select version:",
                range(len(version_options)),
                format_func=lambda x: version_options[x],
                key=f"version_select_{prompt.id}"
            )

            selected_prompt = versions[selected_version_idx]

            md_text = (
                "## Template\n"
                f"{selected_prompt.template}\n"
                "## Example Values\n"
                f"`{selected_prompt.example_values}`"
            )
            st.markdown(md_text)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("👍 Upvote", key=f"upvote_{selected_prompt.id}"):
                    upvote_prompt(selected_prompt.id)
                    st.success("✅ Upvote recorded!")
            with col2:
                if st.button("✏️ Edit", key=f"edit_{selected_prompt.id}"):
                    st.session_state.editing_prompt = selected_prompt
                    st.switch_page(st.Page(show_create_page))
            with col3:
                if st.session_state.delete_confirmation == selected_prompt.id:
                    if st.button("❗ Confirm Delete", key=f"confirm_delete_{selected_prompt.id}"):
                        delete_prompt(selected_prompt.id)
                        st.session_state.delete_confirmation = None
                        st.success("✅ Prompt deleted successfully!")
                        time.sleep(1)
                        st.rerun()
                    if st.button("Cancel", key=f"cancel_delete_{selected_prompt.id}"):
                        st.session_state.delete_confirmation = None
                        st.rerun()
                else:
                    if st.button("🗑️ Delete", key=f"delete_{selected_prompt.id}"):
                        st.session_state.delete_confirmation = selected_prompt.id
                        st.rerun()
            with col4:
                if st.button("📑 Copy Prompt", key=f"copy_{selected_prompt.id}"):
                    clipboard.copy(selected_prompt.template)
                    st.success("✅Copied to clipboard!")