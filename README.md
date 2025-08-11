# Crypto Tax Report Generator

Generates German tax documents for Bitpanda crypto trades.

## Usage

1. Install requirements:
   ```
   pip install -r requirements.txt
   ```

2. Run the script:
   ```
   python script.py --csv upload/bitpanda-trades-YYYY-MM-DD.csv --year 2024 --name "Ihr Name" --street "Ihre Straße" --cityzip "Ihre Stadt und PLZ"
   ```

Output files are saved in the `output` folder.