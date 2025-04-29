# unbound-pom-poc

A Python-based proof-of-concept (PoC) for processing registrations using AI-driven workflows with matcher and critic agents. This project leverages the `autogen-agentchat` library to integrate with OpenAI and Azure AI models, offering multiple workflow configurations for matching registrations to offers and enriching them with pricing and subsidies.

For detailed project specifications, refer to the [PRD - AI PoC POM](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5086445587/PRD+-+AI+PoC+POM) on Confluence.

## Features

- **Modular Workflows**: Three configurations:
  - `p1m1c1_p2m2c2`: Matcher1-Critic1 → Matcher2-Critic2
  - `p1m1_p2m1`: Matcher1 → Matcher2 (no critics)
  - `p1m1m2c`: Matcher1-Critic-Matcher2
- **Model Support**: Compatible with OpenAI and Azure AI models (e.g., DeepSeek-V3).
- **Streaming**: Optional streaming mode for real-time processing.
- **File Management**: JSON-based input/output for registrations, offers, matches, and purchase orders (POs).
- **Execution Tracking**: Logs processing times in CSV format.
- **Utilities**: Modular utility functions for CSV, JSON, token management, and processing.

## Project Structure

```
unbound-pom-poc/
├── igent/
│   ├── agents.py              # Agent creation logic
│   ├── logging_config.py      # Logging setup
│   ├── models/                # Model client configurations
│   │   ├── __init__.py
│   │   ├── azure_deepseek.py  # Azure AI model client
│   │   └── openai.py          # OpenAI model client
│   ├── prompts/               # Prompt loading logic
│   ├── tools/                 # Helper tools
│   │   ├── read_json.py
│   │   └── update_supplier_capacity.py
│   ├── utils/                 # Utility functions
│   │   ├── __init__.py
│   │   ├── csv_utils.py       # CSV handling
│   │   ├── file_paths.py      # File path construction
│   │   ├── json_utils.py      # JSON list management
│   │   ├── processing_utils.py # Pair/group processing
│   │   └── token_utils.py     # Token counting and truncation
│   └── workflows/             # Workflow implementations
│       ├── p1m1c1_p2m2c2.py
│       ├── p1m1_p2m1.py
│       └── p1m1m2c.py
├── data/
│   └── demo/                  # Sample data files
│       ├── sbus_mock_registrations.json
│       ├── sbus_mock_offers.json
│       └── execution_times.csv
├── README.md                  # This file
└── requirements.txt           # Dependencies
```

## Prerequisites

- Python 3.12+
- An OpenAI API key or Azure AI API key (set as environment variables: `OPENAI_API_KEY` or `AZUREAI_API_KEY`)

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/iChoosr-BVBA/unbound-pom-poc.git
   cd unbound-pom-poc
   ```

2. **Set Up a Virtual Environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Environment Variables**:
   Create a `.env` file in the project root with:

   ```bash
   OPENAI_API_KEY="your-openai-api-key"  # For OpenAI
   AZUREAI_API_KEY="your-azure-api-key"  # For Azure
   ```

   Load the environment variables:

   ```bash
   source .env  # On Windows, manually set variables or use a tool like `dotenv`
   ```

## Usage

Run a workflow with sample data from the `data/demo/` directory. Input/output data formats are documented in [Sample & Data Input/Output for AI PoC](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5096472619/Sample+Data+Input+Output+for+AI+PoC) on Confluence.

### Example: `p1m1m2c` Workflow

```python
import asyncio
from igent.workflows.p1m1m2c import run_workflow

async def main():
    line = "sbus"
    await run_workflow(
        model="azure",  # or "openai"
        stream=True,
        business_line=line,
        registrations_file=f"../data/demo/{line}_mock_registrations.json",
        offers_file=f"../data/demo/{line}_mock_offers.json",
        matches_file=f"../data/demo/matches.json",
        pos_file=f"../data/demo/pos.json",
        max_items=2,
        stats_file=f"../data/demo/execution_times.csv"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Workflow Descriptions

- **`p1m1c1_p2m2c2`**:
  - Phase 1: Matcher1 finds matches, Critic1 approves.
  - Phase 2: Matcher2 enriches matches, Critic2 approves.
  - Outputs: `matches.json` (Phase 1), `pos.json` (Phase 2).
- **`p1m1_p2m1`**:
  - Phase 1: Matcher1 finds matches (no critic).
  - Phase 2: Matcher2 enriches matches (no critic).
  - Outputs: `matches.json` (Phase 1), `pos.json` (Phase 2).
- **`p1m1m2c`**:
  - Phase 1: Matcher1 finds matches, Critic approves.
  - Phase 2: Matcher2 enriches matches (no critic).
  - Outputs: `matches.json` (Phase 1), `pos.json` (Phase 2).

For details on the agent workflows, see [Agent work process](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5123440687/Agent+work+process) on Confluence.

### Outputs

- **Matches**: Stored in `matches.json` as a list of JSON objects.
- **Purchase Orders (POs)**: Stored in `pos.json` as a list of enriched JSON objects.
- **Stats**: Execution times saved in `execution_times.csv`.

See [SBUS Input/Output Data for AI PoC & sample](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5124423713/SBUS+Input+Output+Data+for+AI+PoC+sample) for sample data formats.

## Configuration

- **Model**: Set `model="openai"` or `model="azure"` in `run_workflow`.
- **Streaming**: Enable with `stream=True` for real-time output (Azure streaming may require additional tuning).
- **Business Line**: Default is `"sbus"`, adjustable via `business_line`.
- **Max Items**: Limits the number of registrations processed (default: 10).

For model-specific configurations, refer to [Agent framework and AI model comparison](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5086216260/Agent+framework+and+AI+model+comparison) and [DeepSeek R1 Deployment](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5158830201/DeepSeek+R1+Deployment) on Confluence.

## Developer Guide

This section provides detailed instructions for developers to set up, run, debug, and extend the project. Additional technical details are available in the [Handover documentation](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5196546097/Handover+documentation) and [README for Devs](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5240848426/README+for+Devs) on Confluence.

### Setup and Environment

1. **Install Python 3.12+**: Ensure Python is installed and accessible via `python --version`.
2. **Virtual Environment**: Always use a virtual environment to isolate dependencies.
3. **Dependencies**: The `requirements.txt` includes `autogen-agentchat`, `openai`, and other libraries. Install with:

   ```bash
   pip install -r requirements.txt
   ```

4. **API Keys**:
   - Obtain an OpenAI or Azure AI API key from your organization.
   - Store keys in a `.env` file to prevent accidental exposure in version control.
   - Use a library like `python-dotenv` to load environment variables automatically:

     ```python
     from dotenv import load_dotenv
     load_dotenv()
     ```

### Running Workflows

1. **Choose a Workflow**: Select from `p1m1c1_p2m2c2`, `p1m1_p2m1`, or `p1m1m2c` based on your use case. See [Agent work process](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5123440687/Agent+work+process) for workflow details.
2. **Prepare Data**: Use sample data in `data/demo/` or create your own JSON files. Data formats are specified in [SBUS Input/Output Data for AI PoC & sample](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5124423713/SBUS+Input+Output+Data+for+AI+PoC+sample).
3. **Run the Workflow**:
   - Modify the example script in **Usage** to match your configuration.
   - Use `stream=True` for real-time output, but disable it if you encounter Azure streaming issues.
   - Set `max_items` to limit processing for testing.

4. **Prompts**: Prompts are stored in `igent/prompts/`. For SBUS-specific prompts, see [Prompts SBUS](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5130387525/Prompts+SBUS) on Confluence. To create new prompts, follow the guidelines in [Useful links and prompt engineering lectures](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5196972089/Useful+links+and+prompt+engineering+lectures).

### Debugging

- **Logging**: The `logging_config.py` sets up logging. Check logs in the console or configure file-based logging for detailed debugging.
- **Common Issues**:
  - **Invalid JSON**: Validate input JSON files using `igent/utils/json_utils.py`.
  - **Token Limits**: Use `igent/utils/token_utils.py` to monitor and truncate inputs if you hit model token limits.
  - **Agent Errors**: Inspect agent responses in `matches.json` or `pos.json` for unexpected outputs.
- **Performance**: Execution times are logged in `execution_times.csv`. For performance analysis, see [Speed performance](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5203230861/Speed+performance) on Confluence.

### Extending the Project

1. **Add New Workflows**:
   - Create a new file in `igent/workflows/` based on existing workflows.
   - Update `run_workflow` to include your workflow logic.
   - Document the workflow in this `README.md` and on Confluence.
2. **Add New Agents**:
   - Modify `igent/agents.py` to define new matcher or critic agents.
   - Ensure compatibility with existing model clients (`igent/models/`).
3. **Support New Models**:
   - Add a new model client in `igent/models/`.
   - Update configuration logic in `run_workflow` to support the new model.
   - Document model performance in [Agent framework and AI model comparison](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5086216260/Agent+framework+and+AI+model+comparison).
4. **Handle New Business Lines**:
   - Add support for new business lines (e.g., `INNL`, `ENUK`) in workflow scripts.
   - Create corresponding data files in `data/demo/`.
   - Document data formats in Confluence (e.g., [INNL Input/Output Data](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5123309569/INNL+Input+Output+Data+for+AI+PoC+sample)).

### Best Practices

- **Version Control**: Commit changes frequently with descriptive messages. Use feature branches for new development.
- **Testing**: Test workflows with small `max_items` values before processing large datasets.
- **Documentation**: Update this `README.md` and Confluence pages for any changes to workflows, agents, or data formats.
- **Security**: Never commit API keys or sensitive data. Use `.gitignore` to exclude `.env` and output files.

## Troubleshooting

- **Azure Streaming Error (`ValueError: No stop reason found`)**:
  - Set `stream=False` as a workaround.
  - Ensure the Azure model (e.g., DeepSeek-V3) supports streaming and JSON output. See [DeepSeek R1 Deployment](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5158830201/DeepSeek+R1+Deployment).
- **API Key Issues**:
  - Verify `OPENAI_API_KEY` or `AZUREAI_API_KEY` is set correctly in `.env`.
  - Check for typos or expired keys.
- **Missing Dependencies**:
  - Run `pip install -r requirements.txt` again.
  - Ensure Python 3.12+ is used, as some dependencies may not support older versions.
- **JSON Parsing Errors**:
  - Validate JSON files using an online validator or `igent/utils/json_utils.py`.
  - Ensure input files match the expected schema (see [SBUS Input/Output Data](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5124423713/SBUS+Input+Output+Data+for+AI+PoC+sample)).
- **Slow Performance**:
  - Reduce `max_items` for testing.
  - Check [Speed performance](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5203230861/Speed+performance) for optimization tips.

For additional troubleshooting, refer to [Open questions / unknowns](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5091360849/Open+questions+unknowns) on Confluence.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -am 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Document all changes in the pull request and update relevant Confluence pages, such as [Handover documentation](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5196546097/Handover+documentation).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with [autogen-agentchat](https://github.com/microsoft/autogen-agentchat) for agent-based workflows. For evaluation results and project outcomes, see [Evaluation results](https://ichoosr.atlassian.net/wiki/spaces/FF/pages/5236293661/Evaluation+results) on Confluence.
