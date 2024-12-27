# Company Detective

This project summarizes publicly available information about a company. It leverages various APIs to gather and analyze data, providing a comprehensive overview of the target company.

Live site: https://ktrnka.github.io/company-detective

![System diagram](system_diagram.png)

## Features

- Multiple information sources including Crunchbase, news articles, and company websites
- Utilizes AI to analyze and summarize information
- Configured via Airtable
- Google Analytics integration for tracking user interactions and site performance.

## Prerequisites

- Python 3.11 or higher
- uv (Astral's Python package installer and resolver)

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

2. Install uv (if not already installed):
   ```
   make install-uv
   ```

3. Install dependencies using uv:
   ```
   make install
   ```

4. Set up your API keys in a `.env` file in the project root directory.

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

Note: The default goal for the Makefile is set to `build`, so running `make` without arguments will execute the full build process.

## Data Sources

- Crunchbase: Provides detailed company information, funding data, and recent news.
- News Articles: Gathers recent news about the company.
- Company Website: Extracts information directly from the company's official website.
- Reddit: Collects relevant discussions and mentions of the company.
- Glassdoor: Offers employee reviews and sentiment analysis (with improved handling for small companies).
- App Reviews: 
  - Google Play Store: Scrapes up to 100 recent reviews.
  - Apple App Store: Scrapes reviews and downsamples to 100 if more are available, ensuring balanced representation with Google Play reviews.

## Contributing

Contributions are welcome but first contact Keith for more information on how to contribute, as the repository isn't currently set up for open contributions.

## Testing

The project includes automated tests. To run the tests, use:
```
make test
```

Note that some network-based tests may be skipped to avoid dependencies on external services during CI/CD processes.

## Development

To check for dead code, you can use:
```
make vulture
```

## License

To be determined. Please contact the repository owner for licensing information.

## Note

This project is under active development. Some features or data sources may change or be refactored. Please check for updates regularly.
