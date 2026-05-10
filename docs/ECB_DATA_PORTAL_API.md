# ECB Data Portal API - Reference Guide

This document provides a comprehensive reference for accessing macroeconomic and financial data from the European Central Bank (ECB) Data Portal API. All data is publicly available and does not require an API key.

---

## 📖 Quick Start

### Base API URL
```
https://data-api.ecb.europa.eu/service/data/{dataflow}/{series_key}?format={format}&{parameters}
```

### Supported Formats
- `jsondata` - JSON format (recommended for programmatic access)
- `csvdata` - CSV format
- `structurespecificdata` - SDMX-ML 2.1 Structure Specific
- `genericdata` - SDMX-ML 2.1 Generic

### Common Parameters
| Parameter | Description | Example |
|-----------|-------------|---------|
| `format` | Output format | `format=jsondata` |
| `lastNObservations` | Last N observations | `lastNObservations=10` |
| `startPeriod` | Start date (ISO 8601) | `startPeriod=2024-01` |
| `endPeriod` | End date (ISO 8601) | `endPeriod=2024-12` |
| `detail` | Amount of detail | `detail=dataonly` |
| `updatedAfter` | Get updates after timestamp | `updatedAfter=2024-01-01T00:00:00Z` |

### Python Example
```python
import requests
import json

url = "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y?format=jsondata&lastNObservations=1"
response = requests.get(url, timeout=30)
data = json.loads(response.text)
# Extract the latest observation
series = list(data['dataSets'][0]['series'].values())[0]
latest_time, latest_value = list(series['observations'].items())[-1]
print(f"10Y Yield: {latest_value[0]}%")
```

---

## 📊 Dataflows Overview

The ECB Data Portal organizes data into **dataflows** (logical groupings of related datasets).

### Most Relevant Dataflows for Macro Reports

| Dataflow | ID | Description | Key Usage |
|----------|-----|-------------|-----------|
| Exchange Rates | `EXR` | Daily EUR reference rates | Forex data |
| Yield Curves | `YC` | Government bond yields | Bond market analysis |
| Financial Market Data | `FM` | Money market rates, derivatives | Euribor, EONIA, €STR |
| Interest Rate Statistics | `IRS` | Policy rates, deposit rates | ECB policy rates |
| MFI Interest Rate Statistics | `MIR` | Bank lending/deposit rates | Banking sector analysis |
| Harmonised CPI | `HICP` | Inflation data | Consumer prices |
| Consumer Prices | `ICP` | Alternative CPI data | Price indices |
| Financial Stress | `CLIFS` | Composite stress indicators | Risk monitoring |
| Money Market Statistics | `EMMS` | Extended money market data | Liquidity analysis |
| Balance of Payments | `BOP` | International trade/flows | External sector |
| Government Finance | `GFS` | Fiscal data | Public finances |
| Short-Term Statistics | `STS` | Industrial production, retail | Economic activity |

---

## 🔍 Detailed Dataflow References

---

### 1. EXR - Exchange Rates

**Description:** Daily reference exchange rates published by the ECB (16:00 CET).

**Series Key Format:**
```
EXR.{frequency}.{currency}.EUR.SP00.A
```

**Frequency Options:**
- `D` - Daily
- `M` - Monthly average
- `Q` - Quarterly average
- `A` - Annual average

**Available Currencies:**
USD, GBP, JPY, CHF, CNY, CAD, AUD, SEK, NOK, DKK, PLN, HUF, CZK, RON, BGN, HRK, RUB, TRY, ZAR, MXN, BRL, INR, IDR, KRW, SGD, HKD, THB, MYR, PHP, NZD, and many more.

**Examples:**
```
# Daily USD/EUR
EXR.D.USD.EUR.SP00.A

# Daily GBP/EUR  
EXR.D.GBP.EUR.SP00.A

# Daily JPY/EUR
EXR.D.JPY.EUR.SP00.A

# Monthly CNY/EUR
EXR.M.CNY.EUR.SP00.A
```

**API Call:**
```bash
curl "https://data-api.ecb.europa.eu/service/data/EXR/EXR.D.USD.EUR.SP00.A?format=jsondata&lastNObservations=10"
```

---

### 2. YC - Yield Curves

**Description:** Daily euro area zero-coupon yield curves for AAA-rated government bonds.

**Series Key Format:**
```
YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_{maturity}
```

**Available Maturities:**
- Short-term: `1M`, `2M`, `3M`, `6M`, `9M`
- Medium-term: `1Y`, `2Y`, `3Y`, `4Y`, `5Y`
- Long-term: `6Y`, `7Y`, `8Y`, `9Y`, `10Y`, `15Y`, `20Y`, `25Y`, `30Y`

**Examples:**
```
# 2-year yield
YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_2Y

# 10-year yield
YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y

# 30-year yield
YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_30Y
```

**API Call:**
```bash
curl "https://data-api.ecb.europa.eu/service/data/YC/YC.B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y?format=jsondata&lastNObservations=30"
```

**Note:** For US Treasury yields, use OpenBB or FRED instead (ECB focuses on euro area).

---

### 3. FM - Financial Market Data

**Description:** Financial market statistics including money market rates, derivatives, and reference rates.

#### 3a. Euribor Rates

**Series Key Format:**
```
FM.{frequency}.U2.EUR.RT.MM.EURIBOR{tenor}_D_.HSTA
```

**Frequency Options:**
- `D` - Daily
- `M` - Monthly
- `Q` - Quarterly
- `A` - Annual

**Tenor Codes:**
| Code | Tenor | Description |
|------|-------|-------------|
| `1WD` | 1 Week | Spot rate, 1 week maturity |
| `1MD` | 1 Month | Spot rate, 1 month maturity |
| `3MD` | 3 Months | Spot rate, 3 month maturity |
| `6MD` | 6 Months | Spot rate, 6 month maturity |
| `1YD` | 1 Year | Spot rate, 1 year maturity |

**Examples:**
```
# 3-month Euribor (daily)
FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA

# 6-month Euribor (monthly)
FM.M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA
```

#### 3b. EONIA (Euro Overnight Index Average)

**Series Key:**
```
FM.M.U2.EUR.4F.MM.EONIA.HSTA
```

**Note:** EONIA is being phased out in favor of €STR.

#### 3c. €STR (Euro Short-Term Rate)

**Series Key:**
```
FM.M.U2.EUR.4F.MM.UONSTR.HSTA
```

**Description:** The new benchmark rate replacing EONIA. Based on overnight unsecured lending transactions.

**API Call:**
```bash
curl "https://data-api.ecb.europa.eu/service/data/FM/FM.M.U2.EUR.4F.MM.UONSTR.HSTA?format=jsondata&lastNObservations=10"
```

---

### 4. IRS - Interest Rate Statistics

**Description:** Statistical interest rates including ECB policy rates.

**Series Key Format:**
```
IRS.{frequency}.{country}.{sector}.{instrument}.{type}.{currency}.{denomination}.Z
```

**ECB Policy Rates:**
| Rate | Code | Series Key |
|------|------|------------|
| Main Refinancing Rate | MR | `IRS.M.U2.EUR.ECB.MR.0000.EUR.N.Z` |
| Deposit Facility Rate | DF | `IRS.M.U2.EUR.ECB.DF.0000.EUR.N.Z` |
| Marginal Lending Facility | ML | `IRS.M.U2.EUR.ECB.ML.0000.EUR.N.Z` |

**API Call:**
```bash
# Get all ECB policy rates
curl "https://data-api.ecb.europa.eu/service/data/IRS?format=jsondata&lastNObservations=1"
```

---

### 5. HICP / ICP - Inflation Data

**Description:** Harmonised Index of Consumer Prices (HICP) and Indices of Consumer Prices (ICP).

#### HICP (Harmonised Index)

**Series Key Format:**
```
HICP.{frequency}.{country}.{COICOP_category}.{detail}.{statistic}.{unit}
```

**Country Codes:**
- `U` - Euro area (19 or 20 countries)
- `U2` - Euro area (all countries)
- Individual country codes: DE, FR, IT, ES, etc.

**COICOP Categories:**
- `000000` - All-items HICP (overall inflation)
- `001000` - Food and non-alcoholic beverages
- `002000` - Alcoholic beverages and tobacco
- `003000` - Clothing and footwear
- `004000` - Housing, water, electricity, gas
- `005000` - Furniture, household equipment
- And many more...

**Statistic Codes:**
- `INX` - Index (2015=100)
- `ANR` - Annual rate of change (%)
- `MVR` - Monthly rate of change (%)
- `AVR` - Average

**Examples:**
```
# Euro area HICP all-items (index)
HICP.M.U.N.000000.4.INX

# Euro area HICP all-items (annual % change)
HICP.M.U.N.000000.4.ANR
```

**API Call:**
```bash
curl "https://data-api.ecb.europa.eu/service/data/HICP/HICP.M.U.N.000000.4.ANR?format=jsondata&lastNObservations=12"
```

---

### 6. CLIFS - Country-Level Index of Financial Stress

**Description:** Composite indicator measuring financial system stress at the country level.

**Series Key Format:**
```
CLIFS.{frequency}.{country}.CLIFS.A
```

**Examples:**
```
# Euro area financial stress index
CLIFS.M.U.CLIFS.A

# Germany financial stress index
CLIFS.M.DE.CLIFS.A
```

**Interpretation:**
- 0 = Normal stress levels
- >0 = Above-normal stress
- Higher values = Greater financial stress

---

### 7. CISS - Composite Indicator of Systemic Stress

**Description:** Measures systemic stress in the financial system as a whole.

**Series Key:**
```
CISS.M.U.CISS.A
```

---

### 8. BOP - Balance of Payments

**Description:** International transactions data including current account, capital flows, and international investment position.

**Series Key Format:**
```
BOP.{frequency}.{country}.{balance}.{transaction}.{instrument}.{sector}.{counterpart}.A
```

**Examples:**
```
# Euro area current account balance
BOP.Q.U2.N.8.7GR.N.A1.A

# Euro area goods balance  
BOP.Q.U2.N.8.7GS.N.A1.A
```

---

### 9. GFS - Government Finance Statistics

**Description:** Government revenue, expenditure, debt, and deficit data.

**Series Key Format:**
```
GFS.{frequency}.{country}.{sector}.{accounting}.{level}.{classification}.{indicator}...Z
```

**Key Indicators:**
- Government debt as % of GDP
- Government deficit/surplus as % of GDP
- Government revenue and expenditure

---

### 10. STS - Short-Term Statistics

**Description:** High-frequency economic indicators.

**Available Data:**
- Industrial production (volume)
- Industrial producer prices
- Retail trade (volume and value)
- Construction output
- Labour market indicators
- Turnover statistics

**Examples:**
```
# Euro area industrial production
STS.M.U.PROD.N.1000.10.INX
```

---

### 11. MMS - Money Market Survey

**Description:** Survey-based money market data.

---

### 12. EMMS - Extended Money Market Statistics

**Description:** Detailed money market data.

---

## 🎯 Recommended Data for Macro Report

Based on the ECB Data Portal offerings, here are the most valuable additions to your existing report:

### Priority 1: Core Macro Indicators
1. **Euro area yield curve** (YC dataflow)
   - 2Y, 5Y, 10Y, 30Y government bond yields
   - Complements US Treasury data

2. **€STR rate** (FM dataflow)
   - Modern ECB reference rate
   - Replacing EONIA

3. **ECB Policy Rates** (IRS dataflow)
   - Main refinancing rate
   - Deposit facility rate
   - Marginal lending facility rate

4. **Euro area HICP** (HICP dataflow)
   - Overall inflation rate
   - Monthly and annual changes

### Priority 2: Enhanced Coverage
5. **Additional exchange rates** (EXR dataflow)
   - EUR/GBP, EUR/JPY, EUR/CHF
   - Broader forex coverage

6. **EONIA rate** (FM dataflow)
   - Legacy benchmark (being phased out)

7. **Financial stress indicators** (CLIFS/CISS dataflows)
   - Market risk monitoring

### Priority 3: Specialized Data
8. **Balance of Payments** (BOP dataflow)
   - Current account balance
   - Capital flows

9. **Government Finance** (GFS dataflow)
   - Debt-to-GDP ratio
   - Deficit data

10. **Short-Term Statistics** (STS dataflow)
    - Industrial production
    - Retail trade

---

## 🔧 Implementation Notes

### Python Helper Function

```python
import requests
import json
from typing import Optional, Dict, Any

def fetch_ecb_series(
    dataflow: str,
    series_key: str,
    format: str = "jsondata",
    last_n: Optional[int] = None,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Fetch data from ECB Data Portal API.
    
    Args:
        dataflow: Dataflow ID (e.g., 'YC', 'EXR', 'FM')
        series_key: Series key within the dataflow
        format: Output format ('jsondata' or 'csvdata')
        last_n: Number of most recent observations to return
        start_period: Start date (ISO format, e.g., '2024-01')
        end_period: End date (ISO format)
        timeout: Request timeout in seconds
    
    Returns:
        Parsed JSON data or None if error
    """
    url = f"https://data-api.ecb.europa.eu/service/data/{dataflow}/{series_key}"
    params = {"format": format}
    if last_n is not None:
        params["lastNObservations"] = str(last_n)
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        if format == "jsondata":
            return json.loads(response.text)
        return response.text
    except Exception as e:
        print(f"Error fetching ECB data: {e}")
        return None

# Usage example
data = fetch_ecb_series("YC", "B.U2.EUR.4F.G_N_C.SV_C_YM.SR_10Y", last_n=10)
```

### Extracting Latest Value

```python
def get_latest_ecb_value(data: Dict[str, Any]) -> Optional[float]:
    """Extract the latest observation value from ECB JSON data."""
    if not data or "dataSets" not in data or not data["dataSets"]:
        return None
    
    dataset = data["dataSets"][0]
    if "series" not in dataset:
        return None
    
    # Get first (and typically only) series
    series = list(dataset["series"].values())[0]
    if "observations" not in series:
        return None
    
    observations = series["observations"]
    if not observations:
        return None
    
    # Get the most recent observation
    latest_time = max(observations.keys())
    latest_value = observations[latest_time][0]
    
    if latest_value is None:
        return None
    
    try:
        return float(latest_value)
    except (ValueError, TypeError):
        return None

# Usage
value = get_latest_ecb_value(data)
```

---

## 📚 Additional Resources

- **ECB Data Portal:** https://data.ecb.europa.eu/
- **API Documentation:** https://data.ecb.europa.eu/help/api/data
- **Data Examples:** https://data.ecb.europa.eu/help/data-examples
- **SDMX Standards:** https://sdmx.org/

---

## 🔒 API Considerations

1. **Rate Limiting:** The ECB does not publish explicit rate limits, but reasonable usage is expected. Implement caching and avoid frequent polling.

2. **Data Updates:** Most series are updated daily, typically around 16:00 CET.

3. **Historical Data:** Full historical data is available. Use `startPeriod` and `endPeriod` to limit requests.

4. **Error Handling:** The API returns:
   - `200 OK` - Success
   - `400 Bad Request` - Invalid series key or parameters
   - `404 Not Found` - Series does not exist
   - `500 Internal Server Error` - Server-side issues

5. **Caching:** Implement local caching to avoid redundant API calls. Data typically updates once per day.

---

*Last updated: May 2026*
*Source: ECB Data Portal API v2.1*
