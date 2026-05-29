# Spanish Real Estate - Pending API Series Codes

## Status
- **6 indicators** successfully implemented with real API data from INE
- **3 indicators removed** (mortgage_repayment_burden, mortgage_default_rate, mortgage_early_repayments) - API series codes not yet identified
- Report now displays only the 6 working indicators

## Implemented Indicators (Complete)

| Indicator | API Source | Table ID | Series Code |
|-----------|------------|----------|-------------|
| House Price Index | INE | 25171 | IPV769 (value), IPV948 (1Y change), IPV949 (1M change) |
| Average Mortgage Rate | INE | 24460 | HPT64422 |
| New Mortgage Loans Count | INE | 3200 | HPT34618 |
| New Mortgage Loans Value | INE | 3200 | HPT34565 (thousands of euros) |
| Fixed vs Variable Rate Share | INE | 24456 | HPT64401 (fixed), HPT64400 (variable) - calculated as % |
| Mortgage Average Term | INE | 24458 | HPT64412 |

## Pending Indicators (Need API Series Codes)

### 1. Mortgage Repayment Burden
- **Description**: Average mortgage payment as percentage of household income
- **Expected Source**: Bank of Spain - Survey of Household Finances (Encuesta Financiera de las Familias / EFF)
- **Frequency**: Quarterly
- **Notes**: Data from EFF shows median burden declined from 15.8% (2020) to 13.7% (2022)
- **API Endpoint**: BDE BIEST platform
- **Series Pattern**: Likely EFF* or HPT* prefix

### 2. Mortgage Default Rate
- **Description**: Percentage of mortgage loans in arrears (90+ days late)
- **Expected Source**: Bank of Spain - BIEST (morosidad hipotecaria)
- **Frequency**: Quarterly
- **Notes**: BDE defines non-performing loans as >90 days past due on principal/interest
- **API Endpoint**: BDE BIEST platform
- **Series Pattern**: Likely DT* (delinquency/two) prefix

### 3. Mortgage Early Repayments
- **Description**: Volume of early mortgage repayments (refinancing activity)
- **Expected Source**: INE (cancellations/changes) or Bank of Spain
- **Frequency**: Quarterly
- **Notes**: INE mortgage statistics include "cancellations in mortgages" since 2006
- **API Endpoint**: INE wstempus or BDE BIEST
- **Series Pattern**: Likely in INE table range 244xx or 32xx (cancellations)

## API Endpoints to Search

### INE (Instituto Nacional de Estadistica)
- Base URL: `https://servicios.ine.es/wstempus/js/EN/DATOS_TABLA/{table_id}?nult={n}`
- Known mortgage tables: 24456, 24457, 24458, 24460, 25171, 3200
- Potential tables for cancellations: 24481-24499 range (not yet confirmed)

### Bank of Spain (Banco de Espana)
- Base URL: `https://app.bde.es/bierest/resources/srdatosapp/`
- Search endpoint: `listaSeries?idioma=en&series={pattern}`
- Series patterns to try: DT*, EFF*, HPT*, MOROS*

## Resources
- [BDE Interest Rate Statistics](https://www.bde.es/webbe/en/estadisticas/temas/tipos-interes.html)
- [BDE Statistics Main Page](https://www.bde.es/wbe/en/estadisticas/)
- [INE Mortgage Statistics](https://www.ine.es/dyngs/INEbase/en/operacion.htm?c=Estadistica_C&cid=1254736170236&idp=1254735576606)
- [INE Household Income Distribution Atlas](https://www.ine.es/en/componentes_inebase/ADRH_total_nacional.htm)

## Implementation Notes
- All 3 indicators should return `None` for missing data (displays as "NA" in reports)
- Use `unit: ""` for percentage-based indicators to avoid double % sign
- Include `note: "NA - Series code not yet identified"` in indicator metadata
