# LLM Prompt Manager

A Streamlit application for creating, managing, and testing LLM (Large Language Model) prompts with version control capabilities.

## Features

- **Prompt Management**
  - Create and store prompts with template variables
  - Version control for prompts
  - Browse and search existing prompts
  - Upvote useful prompts
  - Copy prompts to clipboard

- **Template System**
  - Jinja2-based templating
  - Variable validation
  - Example value storage

- **Testing Capabilities**
  - Test prompts with multiple LLM endpoints
  - Compare responses from different models
  - Real-time prompt rendering preview

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/llm-prompt-manager.git
cd llm-prompt-manager
```

2. Create a venv:
```bash
uv venv -p 3.11
```

3. Activate venv:
```bash
.venv\bin\activate
```

4. Install dependencies:
```bash
uv pip install -r requirements.txt
```

```

## Configuration

Create a `config.yaml` file in the root directory with your LLM endpoints:

```yaml
endpoints:
  - name: "Llama 3.1 70n"
    url: "your-endpoint-url"
    model: "llama3.1:70b"
    description: "Llama 3.1 70b by Meta"
  
  - name: "Claude"
    url: "your-endpoint-url"
    model: "claude-v1"
    description: "Anthropic Claude Model"
```

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Navigate to the different pages:
   - **Create**: Create new prompts or edit existing ones
   - **Browse**: View and manage existing prompts
   - **Test**: Test prompts with different LLM endpoints

### Creating Prompts

1. Enter prompt details:
   - Name
   - Author
   - Template (using Jinja2 syntax)
   - Example values for variables

2. Test the prompt before saving
3. Save to create a new version

### Managing Versions

- Each prompt edit creates a new version
- Browse page shows latest versions by default
- Select specific versions when viewing prompts
- All versions maintain their own upvote counts

### Testing Prompts

1. Select a prompt from the library
2. Choose the desired version
3. Fill in template variables
4. Select up to 5 LLM endpoints
5. Run the test to compare responses

## Project Structure

```
llm-prompt-manager/
├── app.py
├── config.yaml
├── requirements.txt
├── db_operations.py
├── config_handler.py
├── utils.py
└── pages/
    ├── create_page.py
    ├── browse_page.py
    └── test_page.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.