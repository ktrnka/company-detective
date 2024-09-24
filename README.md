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

3. Set up your API keys in a `.env` file. Here's an example of how your `.env` file should look:

   ```
   OPENAI_API_KEY=your_openai_api_key
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   GOOGLE_CSE_ID=your_google_cse_id
   GOOGLE_API_KEY=your_google_api_key
   SCRAPFLY_API_KEY=your_scrapfly_api_key
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   LANGSMITH_API_KEY=your_langsmith_api_key (optional)
   ```

   Replace `your_*_key` with your actual API keys.

## Usage

The main entry point for running the company analysis is the `src/unified_summary.ipynb` Jupyter notebook. Follow these steps to use the project:

1. Activate the Pipenv shell:
   ```
   pipenv shell
   ```

2. Launch Jupyter Notebook:
   ```
   jupyter notebook
   ```

3. Navigate to `src/unified_summary.ipynb` and open it.

4. Follow the instructions in the notebook to analyze a company.

## Contributing

This repository is not currently set up for open contributions. If you're interested in contributing or have any questions, please contact Keith directly.

## License

To be determined. Please contact the repository owner for more information about licensing.

## Support

If you encounter any issues or have questions about using Company Detective, please open an issue on the GitHub repository or contact the maintainer directly.
