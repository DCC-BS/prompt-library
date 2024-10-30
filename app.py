import streamlit as st

from db_operations import init_db
from pages.browse_page import show_browse_page
from pages.create_page import show_create_page
from pages.test_page import show_test_page
from pages.design_prompt_page import show_design_prompt_page


__version__ = "1.0.0"
__author__ = "data-alchemists des DigiLab BS"
__author_email__ = "data-alchemists@bs.ch"
VERSION_DATE = "2024-10-29"
GIT_REPO = "https://github.com/opendatabs/prompt-library"


def main():
    st.title("LLM Prompt Library")

    init_db()

    if "page" not in st.session_state:
        st.session_state.page = "Browse Prompts"

    st.logo("./assets/logo.jpg", size="large")

    pg = st.navigation(
        {
            "LLM Prompt Library": [
                st.Page(show_browse_page, title="Browse Prompts", icon="📚"),
                st.Page(show_create_page, title="Create New Prompt", icon="✏️"),
                st.Page(show_test_page, title="Test Prompts", icon="🔬"),
                st.Page(show_design_prompt_page, title="Design Prompts", icon="🫕")
            ]
        }
    )

    st.sidebar.image("./assets/logo.jpg")

    show_info_box()

    pg.run()


def show_info_box():
    """
    Displays an information box in the sidebar with author information, version number, and a link to the git repository.
    """
    impressum = f"""<div style="background-color:#34282C; padding: 10px;border-radius: 15px; border:solid 1px white;">
    <small>Autoren: <a href="mailto:{__author_email__}">{__author__}</a><br>
    Version: {__version__} ({VERSION_DATE})<br>
    <a href="{GIT_REPO}">git-repo</a>
    """
    st.sidebar.markdown(impressum, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
