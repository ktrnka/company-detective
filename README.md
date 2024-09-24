# Company Detective

This project summarizes publicly available information about a company. It leverages various APIs to gather and analyze data, providing a comprehensive overview of the target company.

![System diagram](src/system_diagram.png)

## Features

- Aggregates information from multiple sources
- Utilizes AI to summarize and analyze data
- Provides a unified summary of company information

## Prerequisites

- Python 3.10 or higher
- Pipenv

## API Keys Required

This project requires API keys for the following services:

- OpenAI
- Reddit
- Google Custom Search Engine
- Scrapfly
- AWS
- Langsmith (Optional)

Ensure you have obtained the necessary API keys before proceeding with the setup.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/ktrnka/company-detective.git
   cd company-detective
   ```

2. Install dependencies using Pipenv:
   ```
   pipenv install --dev
   ```

3. Set up your API keys as environment variables or in a configuration file (refer to the project documentation for specific instructions on how to set up API keys).

## Usage

The main entry point for running the company analysis is the `src/unified_summary.ipynb` Jupyter notebook.

To run the analysis:

1. Activate the Pipenv shell:
   ```
   pipenv shell
   ```

2. Launch Jupyter Notebook:
   ```
   jupyter notebook
   ```

3. Navigate to `src/unified_summary.ipynb` and open the notebook.

4. Follow the instructions within the notebook to input the company name and run the analysis.

## Contributing

Contributions to improve Company Detective are welcome. Please refer to the `CONTRIBUTING.md` file (if available) for guidelines on how to contribute to this project.

## License

[Include license information here]

## Contact

[Include contact information or link to issues page for questions and support]