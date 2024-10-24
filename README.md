# Company Detective

This project summarizes publicly available information about a company. It leverages various APIs to gather and analyze data, providing a comprehensive overview of the target company.

![System diagram](system_diagram.png)

## Features

- Aggregates information from multiple sources including Crunchbase, Glassdoor, news articles, company websites, and Reddit
- Utilizes AI to summarize and analyze data
- Provides a unified summary of company information
- Dynamic rebuild cadence for up-to-date information

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
- Crunchbase (via Scrapfly)
- Airtable

Ensure you have obtained the necessary API keys before proceeding with the setup. The project is designed to handle missing API keys gracefully, but functionality may be limited without them.

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

## Usage

The main entry points for running the company analysis are:

1. `src/notebooks/entrypoints/refresh_company_data.ipynb`: Use this notebook to refresh company data.
2. `src/notebooks/entrypoints/build_website.ipynb`: Use this notebook to build the website with analyzed data.

## Dynamic Rebuild Cadence

The project features a dynamic rebuild cadence, allowing for more frequent updates of company information. This ensures that the data remains current and relevant.

## Data Sources

- Crunchbase: Provides detailed company information, funding data, and recent news.
- Glassdoor: Offers employee reviews and sentiment analysis.
- News Articles: Gathers recent news about the company.
- Company Website: Extracts information directly from the company's official website.
- Reddit: Collects relevant discussions and mentions of the company.

## Contributing

Contributions are welcome! Please contact Keith for more information on how to contribute, as the repository isn't currently set up for open contributions.

## Testing

The project includes automated tests. Note that some network-based tests may be skipped to avoid dependencies on external services during CI/CD processes.

## License

To be determined. Please contact the repository owner for licensing information.

## Note

This project is under active development. Some features or data sources may change or be refactored. Please check for updates regularly.