# OpenBB Financial Digest Generator
**Objective**: Automate a daily/weekly financial report using OpenBB and custom APIs, with two iterations:
1. **Core Report**: Use OpenBB's built-in data.
2. **Enhanced Report**: Add custom APIs (Euribor, GDELT, etc.).

---

## **📌 Project Overview**
- **Language**: Python
- **Primary Library**: [OpenBB](https://openbb.co/)
- **Output**: PDF/HTML digest report + optional LLM integration (Mistral).
- **Frequency**: Daily or weekly.
- **Data Focus**: Market indices, commodities, macroeconomic indicators, and sociopolitical risks.

---

## **🗂️ Folder Structure**



financial-digest/

│

├── /data                # Raw and processed data (CSV/JSON)

│   ├── openbb_data/      # Data from OpenBB

│   └── custom_data/      # Data from custom APIs

│

├── /scripts             # Python scripts

│   ├── fetch_openbb.py   # Fetch data from OpenBB

│   ├── fetch_custom.py   # Fetch data from custom APIs (Iteration 2)

│   ├── generate_report.py # Generate the digest report

│   └── utils/            # Helper functions (e.g., caching, formatting)

│

├── /reports             # Generated reports (PDF/HTML)

│

├── /notebooks           # Jupyter Notebooks for exploration

│

├── requirements.txt     # Python dependencies

└── README.md            # Project documentation
text
Copy

---

## **🚀 Iteration 1: Core Report (OpenBB Only)**
**Goal**: Generate a digest using **only OpenBB's built-in data sources**.

### **Tasks**
1. **Setup OpenBB**
   - Install OpenBB: `pip install openbb`
   - Test the installation: `openbb terminal`

2. **Define Core Data Points**
   Use OpenBB to fetch:
   | **Category**          | **Data Points**                          | **OpenBB Command**                     |
   |-----------------------|------------------------------------------|----------------------------------------|
   | Market Indexes        | S&P 500, STOXX 600, MSCI World, VIX      | `obb.indices.market("^GSPC")`           |
   | Commodities           | Gold, Brent Crude, Copper, Wheat         | `obb.commodities.gold()`                |
   | Forex                 | USD/EUR, USD/CNY, DXY                   | `obb.forex.rates("USD/EUR")`            |
   | Macroeconomics        | US CPI, EU HICP, US/EU GDP, Unemployment | `obb.economy.cpi()`, `obb.economy.gdp()`|
   | Bonds/Yields          | US 10Y Treasury, German Bunds            | `obb.bonds.yield("DGS10")`              |
   | News                  | Financial headlines                      | `obb.news.company("AAPL")`              |

3. **Create `fetch_openbb.py`**
   - Fetch and cache all core data in `/data/openbb_data/`.
   - Example:
     ```python
     from openbb import obb
     import pandas as pd

     # Fetch S&P 500
     sp500 = obb.indices.market("^GSPC").to_df()
     sp500.to_csv("data/openbb_data/sp500.csv")

     # Fetch US CPI
     cpi = obb.economy.cpi().to_df()
     cpi.to_csv("data/openbb_data/us_cpi.csv")

     # Fetch Gold prices
     gold = obb.commodities.gold().to_df()
     gold.to_csv("data/openbb_data/gold.csv")
     ```

4. **Create `generate_report.py`**
   - Load cached data from `/data/openbb_data/`.
   - Generate:
     - **Executive summary** (1 paragraph).
     - **Market snapshot table** (indices, commodities, forex).
     - **Macroeconomic dashboard** (inflation, GDP, rates).
     - **Visualizations** (e.g., S&P 500 trend, VIX vs. Gold).
   - Export to **PDF/HTML** using `pandas` + `WeasyPrint` or `Plotly` for charts.
   - Example:
     ```python
     import pandas as pd
     from weasyprint import HTML

     # Load data
     sp500 = pd.read_csv("data/openbb_data/sp500.csv")
     cpi = pd.read_csv("data/openbb_data/us_cpi.csv")

     # Generate HTML report
     html = f"""
     <h1>Financial Digest - {pd.Timestamp.today().date()}</h1>
     <h2>Market Snapshot</h2>
     <table>
         <tr><th>Metric</th><th>Value</th><th>1M Change</th></tr>
         <tr><td>S&P 500</td><td>{sp500['close'].iloc[-1]:.2f}</td><td>{sp500['close'].pct_change().iloc[-1]*100:.2f}%</td></tr>
         <tr><td>US CPI</td><td>{cpi['value'].iloc[-1]:.2f}%</td><td>N/A</td></tr>
     </table>
     """
     HTML(string=html).write_pdf("reports/digest.pdf")
     ```

5. **Automate the Report**
   - Use a **cron job** or **Task Scheduler** to run:
     ```bash
     python scripts/fetch_openbb.py && python scripts/generate_report.py
     ```
   - Schedule for **daily at 6 PM CET** or **weekly on Mondays**.

6. **Test Iteration 1**
   - Run the scripts manually and verify the report.
   - Check for **missing data** or **formatting issues**.

---

## **🔄 Iteration 2: Enhanced Report (Custom APIs)**
**Goal**: Add **Euribor, geopolitical risk, supply chain data, and IPO activity** to the report.

### **Tasks**
1. **Add Custom Data Sources**
   | **Data Point**       | **API**                          | **Python Function**                     | **Output File**               |
   |----------------------|----------------------------------|-----------------------------------------|--------------------------------|
   | Euribor              | [ECB API](https://sdw.ecb.europa.eu/) | `fetch_euribor()`                        | `data/custom_data/euribor.json`|
   | Geopolitical Risk    | [GDELT API](https://www.gdeltproject.org/) | `fetch_gdelt()`                   | `data/custom_data/gdelt.json`  |
   | Supply Chain Pressure| [NY Fed API](https://www.newyorkfed.org/) | `fetch_supply_chain()`           | `data/custom_data/supply_chain.json` |
   | IPO Activity         | [Nasdaq API](https://www.nasdaq.com/market-activity/ipos) | `fetch_ipos()` (scrape or API) | `data/custom_data/ipos.csv` |

2. **Create `fetch_custom.py`**
   - Implement functions to fetch and cache custom data.
   - Example for Euribor:
     ```python
     import requests
     import json

     def fetch_euribor():
         url = "https://sdw.ecb.europa.eu/quickview/do/QUERY_LIST/./EXR.D.USD.EUR.SP00.A"
         response = requests.get(url)
         with open("data/custom_data/euribor.json", "w") as f:
             json.dump(response.json(), f)
     ```

3. **Update `fetch_openbb.py`**
   - Call `fetch_custom.py` functions to fetch all custom data.

4. **Update `generate_report.py`**
   - Load custom data from `/data/custom_data/`.
   - Add sections to the report:
     - **Euribor**: Add to the macroeconomic dashboard.
     - **Geopolitical Risk**: Add a "Top Risks" section.
     - **Supply Chain**: Add to the "Emerging Risks" section.
   - Example:
     ```python
     with open("data/custom_data/euribor.json") as f:
         euribor = json.load(f)
     with open("data/custom_data/gdelt.json") as f:
         gdelt = json.load(f)

     html += f"""
     <h2>Macroeconomic Dashboard</h2>
     <p>Euribor (3M): {euribor['value']}%</p>
     <h2>Top Risks</h2>
     <p>Geopolitical Risk: {gdelt['risk_level']}</p>
     """
     ```

5. **Add Traffic-Light Signals**
   - Define thresholds for each metric (e.g., VIX > 20 = 🔴, S&P 500 +2% MoM = 🟢).
   - Example:
     ```python
     def get_signal(value, thresholds):
         if value > thresholds["red"]: return "🔴"
         elif value > thresholds["yellow"]: return "🟡"
         else: return "🟢"

     vix_signal = get_signal(sp500["vix"].iloc[-1], {"red": 20, "yellow": 15})
     ```

6. **Test Iteration 2**
   - Run the updated scripts and verify the enhanced report.
   - Check for **API rate limits** or **errors**.

---
## **📅 Timeline**
| **Phase**               | **Tasks**                                  | **Estimated Time** |
|-------------------------|-------------------------------------------|--------------------|
| Setup OpenBB            | Install, test basic commands              | 1 hour              |
| Iteration 1: Core Report| Fetch data, generate report, automate     | 4-8 hours           |
| Iteration 2: Custom APIs| Add Euribor, GDELT, etc.; update report    | 4-8 hours           |
| Testing & Refinement    | Debug, improve formatting, add visuals   | 2-4 hours           |

---
## **🛠️ Dependencies (`requirements.txt`)**



openbb>=4.0.0

pandas>=2.0.0

weasyprint>=58.0

requests>=2.31.0

matplotlib>=3.8.0

plotly>=5.18.0

jupyter>=1.0.0
text
Copy

---
## **🎯 Next Steps**
1. **Set up the project folder** and install dependencies.
2. **Start with Iteration 1** (OpenBB only) to validate the core report.
3. **Move to Iteration 2** to add custom data sources.
4. **Optional**: Integrate with **Mistral LLM** to generate recommendations from the digest.

---
## **💡 Notes**
- **Data Caching**: Cache all API responses to avoid rate limits (e.g., save to `/data/`).
- **Error Handling**: Add retries for failed API calls.
- **Logging**: Log fetch times and errors for debugging.
- **LLM Integration**: Feed the final report (text or JSON) to Mistral for analysis/recommendations.

