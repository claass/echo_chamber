# Echo Chamber

A LangGraph-based application that creates a council of AI agents to collaboratively produce high-quality responses through multi-round debate and refinement. This project is an experiment for me to play around with multi-agent architectures and handling long-context multi-turn conversations.

## Features

- **Multi-Agent Collaboration**: Draft agent creates initial response, council members provide feedback, editor ensures final quality
- **Configurable Models**: Choose different OpenAI models for each agent role
- **Interactive Debate**: Configurable number of debate rounds for iterative improvement
- **Simple CLI**: Clean command-line interface with Rich library for formatted output
- **Persistent Configuration**: Save API keys and preferences for future sessions

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your OpenAI API key (choose one method):

   **Method 1: Environment Variable (Recommended)**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

   **Method 2: .env File (Recommended for development)**
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

   **Method 3: Interactive Setup**
   The app will prompt you for the API key on first run and save it to `.env`

3. Run the application:
```bash
python main.py
```

## Security Notes

🔒 **API Key Security**: This application follows security best practices:
- API keys are stored in environment variables or `.env` files
- Configuration files (`council_config.json`) do not contain API keys
- The `.env` file and old `config.json` are in `.gitignore`
- If you have an old `config.json` with an API key, it will be automatically migrated

## Usage

On first run, you'll be prompted to:
1. Enter your OpenAI API key (stored securely in local config)
2. Select models for each agent role:
   - Draft Agent (creates initial responses)
   - Council Members (provide feedback)
   - Editor Agent (final polish)
3. Choose number of council members and debate rounds

### CLI Features

- **Progress Indicators**: Real-time progress updates during processing
- **Rich Formatting**: Markdown rendering for responses with syntax highlighting
- **Simple Interaction**: Enter queries directly, type 'quit' to exit
- **Automatic Save**: Responses automatically saved to `council_response.txt`

## Architecture

- `agents.py`: Agent implementations (DraftAgent, CouncilMember, EditorAgent)
- `workflow.py`: LangGraph workflow orchestrating the debate process
- `config_manager.py`: Configuration management and persistence
- `simple_cli.py`: Command-line interface with Rich formatting
- `main.py`: Application entry point
- `secure_config.py`: Secure configuration management

## Output

Final responses are saved to `council_response.txt` for each query.

## Example Prompts to Try

1. **Technical Explanation**: "Explain the concept of quantum computing in simple terms, including its potential applications and current limitations."

2. **Creative Writing**: "Write a short story about a robot who discovers it has emotions for the first time."

3. **Problem Solving**: "Design a sustainable urban transportation system for a city of 2 million people, considering environmental impact, cost, and accessibility."

4. **Educational Content**: "Create a lesson plan for teaching the water cycle to 5th grade students, including interactive activities and assessment methods."

5. **Business Analysis**: "Analyze the pros and cons of remote work for both employers and employees, and suggest best practices for hybrid work models."

These prompts showcase how the multi-agent debate process can enhance responses through iterative refinement and multiple perspectives.