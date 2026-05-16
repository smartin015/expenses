# Expense Tools

This is a collection of simple scripts and utilities to collect, annotate, and export expenses from individual sources.

## Expense Parser

Parse CSV dumps of expenses from Splitwise, credit card companies etc. with **AI-powered categorization** for uncategorized expenses.

### Features

- **Manual Rules**: Configure regex-based categorization rules for known merchants
- **AI Categorization**: Automatically categorize unknown expenses using ChatGPT
- **Smart Caching**: Cache AI categorizations to reduce API costs
- **Multiple Formats**: Support CSV and JSON input files

### Configuration

Configs are located in `expense_parser/config`:

* `manifest.yaml` selects a specific rule CSV file based on a matching header column. It also contains parsing config and mapping of header names to useful columns.
* `*.csv` files are a list of manual rules that normalize the categories provided by each input CSV.
  * The first column is what to match on (e.g. category vs description), the second is the category to write, and the third is a regular expression for matching the particular category or description text.
  * Rules are evaluated in descending order, so earlier rules match first.
* `ai_categorizations.csv` automatically stores AI-generated categorizations for caching.

### Installation

```bash
cd expense_parser
pip3 install -r requirements.txt

# Optional: Set up AI categorization
export OPENAI_API_KEY="your-api-key-here"
```

### Usage

```bash
# Basic usage
python3 parse_expenses.py --prev previous_output.csv --paths input1.csv input2.csv

# Disable AI categorization
python3 parse_expenses.py --prev previous_output.csv --paths input1.csv --disable-ai

# Save output to file
python3 parse_expenses.py --prev previous_output.csv --paths input1.csv > out.csv
```

Log messages are written to stderr, so only output rows are written to the file (via stdout).

### AI Categorization

See [AI_CATEGORIZATION.md](expense_parser/AI_CATEGORIZATION.md) for detailed information about the AI categorization feature.

## Price Fetcher

Fetch prices of specific goods to help with computing a personal [Consumer Price Index](https://en.wikipedia.org/wiki/Consumer_price_index). 

Items and queries are currently quite hardcoded. 
