import streamlit as st

from db_operations import init_db
from pages.browse_page import show_browse_page
from pages.create_page import show_create_page
from pages.test_page import show_test_page


def main():
    st.title("Prompt Library")

    init_db()

    if "page" not in st.session_state:
        st.session_state.page = "Browse Prompts"

    pg = st.navigation(
        [
            st.Page(show_browse_page, title="Browse Prompts", icon="📚"),
            st.Page(show_create_page, title="Create New Prompt", icon="✏️"),
            st.Page(show_test_page, title="Test Prompts", icon="🔬"),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
