# unbound-pom-poc

A Python-based proof-of-concept (PoC) for processing registrations using AI-driven workflows with matcher and critic agents. This project leverages the `autogen-agentchat` library to integrate with OpenAI and Azure AI models, offering multiple workflow configurations for matching registrations to offers and enriching them with pricing and subsidies.

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
   Create `.env` file with:

   ```bash
   export OPENAI_API_KEY="your-openai-api-key"  # For OpenAI
   export AZUREAI_API_KEY="your-azure-api-key"  # For Azure
   ```

## Usage

Run a workflow with sample data from the `data/demo/` directory.

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

### Outputs

- **Matches**: Stored in `matches.json` as a list of JSON objects.
- **Purchase Orders (POs)**: Stored in `pos.json` as a list of enriched JSON objects.
- **Stats**: Execution times saved in `execution_times.csv`.

## Configuration

- **Model**: Set `model="openai"` or `model="azure"` in `run_workflow`.
- **Streaming**: Enable with `stream=True` for real-time output (Azure streaming may require additional tuning).
- **Business Line**: Default is `"sbus"`, adjustable via `business_line`.
- **Max Items**: Limits the number of registrations processed (default: 10).

## Troubleshooting

- **Azure Streaming Error (`ValueError: No stop reason found`)**:
  - Try `stream=False` as a workaround.
  - Ensure the Azure model (e.g., DeepSeek-V3) supports streaming and JSON output.
- **API Key Issues**:
  - Verify `OPENAI_API_KEY` or `AZUREAI_API_KEY` is set correctly.
- **Missing Dependencies**:
  - Run `pip install -r requirements.txt` again if errors occur.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -am 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with [autogen-agentchat](https://github.com/microsoft/autogen-agentchat) for agent-based workflows.
