import streamlit as st
import json
from db_operations import *
from jinja2 import Template
import jinja2
import asyncio
import aiohttp
import time

async def test_prompt_with_model(url: str, prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"prompt": prompt}) as response:
                result = await response.json()
                return result.get('response', 'Error: No response received')
        except Exception as e:
            return f"Error: {str(e)}"

async def test_multiple_models(urls: List[str], prompt: str) -> dict:
    tasks = [test_prompt_with_model(url, prompt) for url in urls]
    results = await asyncio.gather(*tasks)
    return dict(zip(urls, results))

def main():
    st.title("Prompt Library")
    
    # Initialize database
    init_db()

    if 'page' not in st.session_state:
        st.session_state.page = "Browse Prompts"
    
    # Sidebar navigation
    st.session_state.page = st.sidebar.selectbox(
        "Choose a page",
        ["Browse Prompts", "Create New Prompt", "Test Prompts"],
        index=["Browse Prompts", "Create New Prompt", "Test Prompts"].index(st.session_state.page)
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

    if 'delete_confirmation' not in st.session_state:
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
    
    editing_prompt = st.session_state.get('editing_prompt')
    
    name = st.text_input("Prompt Name", value=editing_prompt.name if editing_prompt else "")
    author = st.text_input("Author", value=editing_prompt.author if editing_prompt else "")
    template = st.text_area("Prompt Template (Use {{variable}} for template variables)",
                           value=editing_prompt.template if editing_prompt else "")
    example_values = st.text_area("Example Values (JSON format)",
                                 value=editing_prompt.example_values if editing_prompt else "{}")
    
    if st.button("Save Prompt"):
        try:
            # Validate JSON format for example values
            validate_example_values = json.loads(example_values)
            
            # Validate Jinja template
            validate_template = Template(template)
            
            # Validate example values for each template value:
            validate_template.render(validate_example_values)
            
            prompt = Prompt(
                id=editing_prompt.id if editing_prompt else None,
                name=name,
                author=author,
                template=template,
                example_values=example_values,
                upvotes=editing_prompt.upvotes if editing_prompt else 0
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
            raise e
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



def show_test_page():
    st.header("Test Prompts")
    
    prompts = get_all_prompts()
    selected_prompt = st.selectbox(
        "Select a prompt to test",
        options=prompts,
        format_func=lambda x: x.name
    )
    
    if selected_prompt:
        # Display template and create input fields for variables
        st.subheader("Template")
        st.text(selected_prompt.template)
        
        # Parse template to find variables
        template = Template(selected_prompt.template)
        variables = get_template_variables(selected_prompt.template)
        
        # Create input fields for variables
        values = {}
        for var in variables:
            values[var] = st.text_input(f"Value for {var}")
        
        # Model endpoints
        st.subheader("Model Endpoints")
        num_models = st.number_input("Number of models to test", min_value=1, value=1)
        model_urls = []
        for i in range(num_models):
            url = st.text_input(f"Model {i+1} endpoint URL")
            if url:
                model_urls.append(url)
        
        if st.button("Test Prompt"):
            try:
                # Render template with provided values
                rendered_prompt = template.render(**values)
                st.subheader("Rendered Prompt")
                st.text(rendered_prompt)
                
                # Test with multiple models
                if model_urls:
                    results = asyncio.run(test_multiple_models(model_urls, rendered_prompt))
                    
                    st.subheader("Results")
                    for url, response in results.items():
                        st.write(f"**Model ({url}):**")
                        st.write(response)
                        st.markdown("---")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()