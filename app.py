import streamlit as st
import json
from db_operations import *
from jinja2 import Template
import jinja2
import asyncio
import aiohttp

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
    
    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Browse Prompts", "Create New Prompt", "Test Prompts"]
    )
    
    if page == "Browse Prompts":
        show_browse_page()
    elif page == "Create New Prompt":
        show_create_page()
    elif page == "Test Prompts":
        show_test_page()

def show_browse_page():
    st.header("Browse Prompts")
    prompts = get_all_prompts()
    
    for prompt in prompts:
        with st.expander(f"{prompt.name} by {prompt.author} (👍 {prompt.upvotes})"):
            st.text_area("Template", prompt.template, height=100, key=f"template_{prompt.id}")
            st.text_area("Example Values", prompt.example_values, height=50, key=f"examples_{prompt.id}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Upvote", key=f"upvote_{prompt.id}"):
                    upvote_prompt(prompt.id)
                    st.rerun()
            with col2:
                if st.button("Edit", key=f"edit_{prompt.id}"):
                    st.session_state.editing_prompt = prompt
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
            json.loads(example_values)
            
            # Validate Jinja template
            Template(template)
            
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
            else:
                save_prompt(prompt)
                
            st.success("Prompt saved successfully!")
            st.session_state.editing_prompt = None
            st.rerun()
            
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