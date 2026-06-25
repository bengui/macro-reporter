# Macro Economic Financial Report Service

A Python service that generates daily/weekly macroeconomic financial reports using OpenBB and custom APIs.

## Features

- **Core Report (Iteration 1)**: Market indices, commodities, forex, macroeconomic indicators, bonds/yields, and news from OpenBB
- **Enhanced Report (Iteration 2)**: Additional data from Euribor, GDELT, NY Fed Supply Chain, and Nasdaq IPOs
- **Output**: PDF and HTML reports
- **Visualizations**: Charts and tables for key metrics
- **Traffic Light Signals**: Color-coded indicators for risk assessment

## Project Structure

```
macro_reporter/
├── data/
│   ├── openbb_data/      # Data from OpenBB
│   └── custom_data/      # Data from custom APIs
├── scripts/
│   ├── fetch_openbb.py   # Fetch data from OpenBB
│   ├── fetch_ecb.py       # Fetch ECB data
│   ├── fetch_gdelt.py     # Fetch GDELT geopolitical data
│   ├── fetch_supply_chain.py # Fetch NY Fed supply chain data
│   ├── fetch_ipos.py      # Fetch IPO activity data
│   ├── fetch_spanish_real_estate.py # Fetch Spanish real estate data
│   ├── fetch_all.py       # Fetch all custom data sources
│   ├── generate_report.py # Generate the digest report
│   └── utils/            # Helper functions
├── reports/             # Generated reports (PDF/HTML)
├── notebooks/           # Jupyter Notebooks for exploration
├── pyproject.toml
└── README.md
```

## Setup

### Prerequisites
- Python 3.10+
- uv (for dependency management)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd macro_reporter

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### Quick Start

```bash
# Fetch data from OpenBB
python scripts/fetch_openbb.py

# Generate report
python scripts/generate_report.py

# Or run both
python scripts/fetch_openbb.py && python scripts/generate_report.py
```

## Usage

### Fetch Data

```bash
# Fetch only OpenBB data
python scripts/fetch_openbb.py

# Fetch all custom API data
python scripts/fetch_all.py

# Or fetch individual custom data sources
python scripts/fetch_ecb.py
python scripts/fetch_gdelt.py
python scripts/fetch_supply_chain.py
python scripts/fetch_ipos.py
python scripts/fetch_spanish_real_estate.py

# Fetch all data
python scripts/fetch_openbb.py && python scripts/fetch_all.py
```

### Generate Reports

```bash
# Generate daily report
python scripts/generate_report.py --type daily --output pdf

# Generate weekly report
python scripts/generate_report.py --type weekly --output html
```

## Configuration

Edit the configuration in each script to customize:
- Data sources
- Report frequency
- Output format
- File paths

## Data Sources

### OpenBB (Core Report)
- Market Indices: S&P 500, STOXX 600, MSCI World, VIX
- Commodities: Gold, Brent Crude, Copper, Wheat
- Forex: USD/EUR, USD/CNY, DXY
- Macroeconomics: US CPI, EU HICP, US/EU GDP, Unemployment
- Bonds/Yields: US 10Y Treasury, German Bunds
- News: Financial headlines

### Custom APIs (Enhanced Report)
- Euribor: ECB API
- Geopolitical Risk: GDELT API
- Supply Chain Pressure: NY Fed API
- IPO Activity: Nasdaq API

## Scheduling

### Cron Job (Linux/macOS)

For daily reports at 6 PM CET:
```bash
0 18 * * * /path/to/venv/bin/python /path/to/macro_reporter/scripts/fetch_openbb.py && /path/to/venv/bin/python /path/to/macro_reporter/scripts/generate_report.py --type daily
```

For weekly reports on Mondays:
```bash
0 18 * * 1 /path/to/venv/bin/python /path/to/macro_reporter/scripts/fetch_openbb.py && /path/to/venv/bin/python /path/to/macro_reporter/scripts/generate_report.py --type weekly
```

### Task Scheduler (Windows)

Create a scheduled task to run the scripts at your desired frequency.

## Output

Reports are generated in the `reports/` directory:
- `daily_report_YYYY-MM-DD.pdf`
- `weekly_report_YYYY-MM-DD.pdf`
- `daily_report_YYYY-MM-DD.html`
- `weekly_report_YYYY-MM-DD.html`

## License

MIT
