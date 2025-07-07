# Portfolio Rebalancing Tool

A comprehensive Python tool for rebalancing investment portfolios with detailed fee calculations for Interactive Brokers (IBKR) trading across multiple exchanges.

## Features

- **Multi-Portfolio Support**: Manage multiple portfolios with different allocation strategies
- **Global Cash Contributions**: Distribute cash contributions across portfolios based on contribution percentages
- **Multi-Currency Support**: Handle CHF, USD, EUR, CAD, and other currencies with automatic exchange rate conversion
- **Detailed Fee Calculations**: Calculate trading fees for major exchanges (Swiss EBS, NYSE Arca, XETRA, Toronto TSX)
- **Spread Cost Analysis**: Track bid-ask spread costs in the ticker's native currency
- **NAV Deviation Warnings**: Alert when market prices significantly deviate from Net Asset Value
- **Flexible Trading Options**: Compare whole shares vs. fractional shares vs. rounded-up shares
- **Fee Structure Comparison**: Compare IBKR tiered vs. fixed pricing models

## Supported Exchanges

- **Swiss Exchange (EBS)** - CHF denominated ETFs
- **NYSE Arca** - USD denominated ETFs
- **XETRA/GER** - EUR denominated ETFs  
- **Toronto (TSX)** - CAD denominated ETFs
- **NASDAQ** - USD denominated ETFs

## Installation

```bash
python3 -m venv finance_env
source finance_env/bin/activate
pip install yfinance
```

## Usage

```bash
python3 rebalance.py -f allocations.json
```

## Configuration

### Portfolio Configuration (allocations.json)

The tool uses a JSON configuration file to define portfolios and their target allocations:

```json
{
  "allocations": {
    "conservative": {
      "name": "Conservative Portfolio",
      "description": "Conservative allocation with 30% cash reserve",
      "contribution_percentage": 0.80,
      "holdings": {
        "AVDV": 0.10,
        "AVUV": 0.10,
        "GOAT.SW": 0.20,
        "4GLD.DE": 0.05,
        "ZGLD.TO": 0.05,
        "ZGLD.SW": 0.05,
        "SRECHA.SW": 0.10,
        "VNQ": 0.05,
        "CHF": 0.30
      }
    },
    "satellite": {
      "name": "Satellite Portfolio", 
      "description": "High-risk leveraged ETF allocation",
      "contribution_percentage": 0.20,
      "holdings": {
        "TQQQ": 0.25,
        "UGLD": 0.25,
        "TMF": 0.25,
        "DRN": 0.25
      }
    }
  }
}
```

### Required Fields

- **name**: Portfolio display name
- **description**: Portfolio description
- **contribution_percentage**: Decimal percentage of total contributions (must sum to 1.0 across all portfolios)
- **holdings**: Dictionary of ticker symbols and their target allocations (must sum to 1.0)

### Supported Assets

- **ETFs/ETCs**: Any ticker symbol supported by Yahoo Finance
- **Cash**: Use currency codes (CHF, USD, EUR, CAD, etc.)

## Interactive Process

The tool will prompt you for:

1. **Global Cash Contributions**: Total CHF and USD contributions to distribute across portfolios
2. **Current Holdings**: Number of shares held for each ticker in each portfolio
3. **Current Cash**: Current CHF and USD cash balances for each portfolio

## Output

The tool provides:

### Current Portfolio Status
- Current ETF positions and values
- Cash balances in USD equivalent
- Current vs. target allocation percentages

### Rebalancing Recommendations
- Buy/sell recommendations for each ticker
- Detailed fee breakdowns (commission, exchange fees, regulatory fees)
- Spread cost analysis
- Comparison of different share quantities (whole, exact, rounded-up)

### Fee Optimization
- Comparison between IBKR tiered vs. fixed pricing
- Trades sorted by optimal pricing model
- Separate sections for buy and sell orders

### Verification
- Portfolio value reconciliation
- Cash allocation verification
- Warning alerts for significant deviations

## Data Classes

### TradeDTO
Represents a trade recommendation with detailed fee analysis:
- `ticker`: ETF ticker symbol
- `is_buy`: Boolean indicating buy (True) or sell (False)
- `currency`: Trading currency
- `exchange`: Exchange name
- `warning_message`: Any alerts or warnings
- `spread_fee`: Bid-ask spread cost in ticker's currency
- `rounded_down/exact/rounded_up`: Share scenarios with associated fees

### ShareTypeData
Contains fee calculations for different share quantities:
- `shares`: Number of shares
- `value`: Trade value in local currency
- `tiered_fee`: Total fees under IBKR tiered pricing
- `fixed_fee`: Total fees under IBKR fixed pricing

## Exchange-Specific Features

### Swiss EBS Exchange
- Handles CHF-denominated ETFs
- Includes EBS exchange fees, clearing fees, and trade reporting fees
- Supports both whole share and fractional share trading

### US Exchanges (NYSE Arca, NASDAQ)
- USD-denominated ETFs
- FINRA fees, clearing fees, and exchange-specific fees
- Assumes liquidity removal for conservative fee estimates

### European Exchanges (XETRA)
- EUR-denominated ETFs
- German regulatory fees and IBIS exchange fees
- Smart routing vs. directed routing fee comparison

### Canadian TSX
- CAD-denominated ETFs
- TSX-specific exchange and regulatory fees

## Limitations

- Requires Yahoo Finance data availability
- Exchange rates fetched in real-time
- Fee calculations based on IBKR pricing as of implementation date
- Some exchanges may have placeholder fee calculations

## Risk Warnings

- **NAV Deviation Alerts**: Warns when market price deviates >1% from Net Asset Value
- **Portfolio Verification**: Ensures final portfolio value matches initial value
- **Cash Allocation Checks**: Verifies remaining cash matches target allocation

## License

This tool is for educational and personal use. Users are responsible for verifying all calculations and fee structures with their broker before executing trades.