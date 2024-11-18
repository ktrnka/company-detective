# Company Detective

This project summarizes publicly available information about a company. It leverages various APIs to gather and analyze data, providing a comprehensive overview of the target company.

![System diagram](system_diagram.png)

## Features

- Aggregates information from multiple sources including Crunchbase, news articles, and company websites
- Utilizes AI to summarize and analyze data
- Provides a unified summary of company information
- Dynamic rebuild cadence for up-to-date information
- Parallel local scraping for improved performance
- Asynchronous operations for faster data collection

## Prerequisites

- Python 3.11 or higher
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
   make install
   ```

3. Set up your API keys in a `.env` file in the project root directory.

## Usage

The main commands for running the company analysis are:

1. To refresh company data:
   ```
   make refresh-data
   ```

2. To build the website with analyzed data:
   ```
   make build-website
   ```

3. To perform both operations sequentially:
   ```
   make build
   ```

## Dynamic Rebuild Cadence

The project features a dynamic rebuild cadence, allowing for more frequent updates of company information. This ensures that the data remains current and relevant.

## Data Sources

- Crunchbase: Provides detailed company information, funding data, and recent news.
- News Articles: Gathers recent news about the company using asynchronous scraping.
- Company Website: Extracts information directly from the company's official website using parallel local scraping.
- Reddit: Collects relevant discussions and mentions of the company.
- Glassdoor: Offers employee reviews and sentiment analysis (with improved handling for small companies).

## Performance Improvements

- Parallel Local Scraping: Implemented to improve the speed of data collection from company websites and news articles.
- Asynchronous Operations: Utilized for faster and more efficient data gathering, particularly for news articles and company webpages.

## Contributing

Contributions are welcome! Please contact Keith for more information on how to contribute, as the repository isn't currently set up for open contributions.

## Testing

The project includes automated tests. Note that some network-based tests may be skipped to avoid dependencies on external services during CI/CD processes.

## License

To be determined. Please contact the repository owner for licensing information.

## Note

This project is under active development. Some features or data sources may change or be refactored. Please check for updates regularly.