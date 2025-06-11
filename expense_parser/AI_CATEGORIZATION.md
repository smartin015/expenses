# AI Categorization Feature

The expense parser now supports automatic categorization of uncategorized expenses using ChatGPT with intelligent caching.

## How It Works

1. **Manual Rules First**: The parser first attempts to categorize expenses using the existing manual rules in the `config/*.csv` files.

2. **AI Fallback**: If no manual rule matches and the expense has no category, the AI categorizer is consulted.

3. **Cache Check**: Before calling ChatGPT, the system checks if this exact description has been categorized before using a local CSV cache.

4. **ChatGPT API Call**: If not found in cache, the system calls ChatGPT to categorize the expense into one of the predefined categories.

5. **Cache Storage**: The AI-generated categorization is automatically saved to the cache for future use.

## Setup

### 1. Install Dependencies

The AI categorization requires the OpenAI Python client:

```bash
cd expense_parser
pip install -r requirements.txt
```

### 2. Set API Key

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Usage

The AI categorization is enabled by default. Use the parser as normal:

```bash
python3 parse_expenses.py --prev previous_output.csv --paths input1.csv input2.csv
```

To disable AI categorization:

```bash
python3 parse_expenses.py --prev previous_output.csv --paths input1.csv input2.csv --disable-ai
```

## Categories

The AI categorizer uses these predefined categories:

- **Food**: Restaurants, groceries, food delivery
- **Merch**: General merchandise, shopping, online purchases
- **Travel**: Transportation, hotels, travel-related expenses
- **Recurring**: Subscriptions, recurring payments
- **Healthcare**: Medical, pharmacy, health-related
- **Utilities**: Electric, gas, water, internet, phone
- **Entertainment**: Movies, games, streaming services
- **Transportation**: Gas, public transit, rideshare
- **Home**: Home improvement, furniture, household items
- **Personal**: Personal care, clothing
- **Other**: Everything else

## Cache File

AI categorizations are stored in `config/ai_categorizations.csv` with the format:

```csv
# AI-generated expense categorizations cache
# Format: description_hash,description,category,timestamp
abcd1234,AMAZON.COM,Merch,2025-06-01T00:00:00
efgh5678,STARBUCKS,Food,2025-06-01T00:00:00
```

- **description_hash**: MD5 hash of the lowercase description (first 16 characters)
- **description**: Original expense description
- **category**: AI-assigned category
- **timestamp**: When the categorization was made

## Cost Considerations

The AI categorization uses OpenAI's GPT-3.5-turbo model, which costs approximately $0.0015 per 1K tokens. Each categorization request typically uses ~100 tokens, so the cost is roughly $0.00015 per uncategorized expense.

The caching system ensures that identical expense descriptions are only categorized once, significantly reducing API costs for recurring expenses.

## Customization

### Adding Custom Categories

To add custom categories, modify the `existing_categories` list in the `AICategorizer` class constructor in `parse_expenses.py`.

### Adjusting the AI Prompt

The categorization prompt can be customized in the `categorize` method of the `AICategorizer` class.

## Troubleshooting

### "OPENAI_API_KEY not set" Warning

This is normal if you haven't set up the API key. The system will still work using cached categorizations and manual rules.

### Cache Not Working

Ensure the `config/ai_categorizations.csv` file exists and has proper read/write permissions.

### Unexpected Categories

The AI occasionally returns categories not in the predefined list. The system automatically falls back to "Other" in such cases.

## Example

```bash
# First run - some expenses get categorized by AI
$ python3 parse_expenses.py --prev out.csv --paths new_expenses.csv
INFO:main:AI categorized: CVS PHARMACY 123 -> Healthcare
INFO:main:AI categorized: NETFLIX.COM -> Entertainment
2025-08-01, "CVS PHARMACY 123", Healthcare, 25.47
2025-08-02, "NETFLIX.COM", Entertainment, 15.99

# Second run - same expenses use cache
$ python3 parse_expenses.py --prev out.csv --paths new_expenses.csv
INFO:main:Using cached AI categorization: CVS PHARMACY 123 -> Healthcare
INFO:main:Using cached AI categorization: NETFLIX.COM -> Entertainment
```
