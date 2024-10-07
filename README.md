# Company Detective

This project summarizes publicly available information about a company. It leverages various APIs to gather and analyze data, providing a comprehensive overview of the target company.

![System diagram](system_diagram.png)

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

3. Set up your API keys in a `.env` file in the project root directory.

## Project Structure

The project is organized as follows:

- `src/`: Main source code directory
  - `data_sources/`: Contains modules for different data sources (e.g., app stores, glassdoor, news, reddit)
  - `notebooks/`: Jupyter notebooks for various tasks and tests
  - `utils/`: Utility functions and helpers

## Usage

The main entry points for running the company analysis are:

1. `src/notebooks/entrypoints/refresh_company_data.ipynb`: Use this notebook to refresh company data.
2. `src/notebooks/entrypoints/build_website.ipynb`: Use this notebook to build the website with analyzed data.

To run these notebooks:

1. Start a Jupyter server:
   ```
   pipenv run jupyter lab
   ```

2. Navigate to the desired notebook in the `src/notebooks/entrypoints/` directory.

3. Follow the instructions within the notebook to run the analysis.

## Contributing

Contributions are welcome! Please talk to Keith for more information on how to contribute, as the repo isn't currently set up for open contributions.

## License

To be determined. Please contact the repository owner for licensing information.

## Note

This project is under active development. Some features or data sources may change or be refactored. Always refer to the most recent documentation or contact the maintainers for the latest information.