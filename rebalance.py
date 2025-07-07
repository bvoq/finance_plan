#!/usr/bin/env python3
import yfinance as yf
import sys
import json
import argparse
from dataclasses import dataclass

@dataclass
class TickerData:
    symbol: str
    currency: str
    fullExchangeName: str
    bid: float
    ask: float
    navPrice: float
    yf_object: object

@dataclass
class ShareTypeData:
    shares: float
    value: float
    tiered_fee: float
    fixed_fee: float

@dataclass
class TradeDTO:
    ticker: str
    is_buy: bool
    currency: str
    exchange: str
    warning_message: str
    rounded_down: ShareTypeData
    rounded_up: ShareTypeData
    exact: ShareTypeData
    spread_fee: float

@dataclass
class PortfolioDTO:
    key: str
    name: str
    ticker_holdings: dict[str, float]
    cash_allocations: dict[str, float]
    contribution_percentage: float

def get_current_price(ticker):
    """
    Retrieve the most recent closing price for a given ticker using yfinance.
    """
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="1d")
        if hist.empty:
            raise ValueError(f"No price data found for {ticker}.")
        return hist['Close'].iloc[0]
    except Exception as e:
        print(f"Error retrieving data for {ticker}: {e}")
        return None

def prompt_holdings(target_allocations, portfolio_name=""):
    """Prompt the user for the number of shares held for each ticker."""
    shares = {}
    if portfolio_name:
        print(f"\nEntering holdings for {portfolio_name}:")
    for ticker in target_allocations:
        if ticker == "CHF":
            continue
        while True:
            try:
                prompt = f"Enter {portfolio_name} shares held for {ticker}: " if portfolio_name else f"Enter number of shares held for {ticker}: "
                share_count = float(input(prompt))
                shares[ticker] = share_count
                break
            except ValueError:
                print("Invalid input. Please enter a number.")
    return shares

def prompt_cash_contributions(exchange_rates):
    """
    Ask for global cash contributions in CHF and USD. Positive = add, negative = withdraw, 0 = no change.
    This will be distributed across portfolios based on their contribution percentages.
    """
    print("\nGlobal cash contributions (will be distributed across portfolios):")
    print("(Enter positive to add, negative to withdraw, 0 for no change)")
    
    while True:
        try:
            contribution_chf = float(input("  Total CHF contribution: ") or "0")
            break
        except ValueError:
            print("  Invalid input. Please enter a number.")
    
    while True:
        try:
            contribution_usd = float(input("  Total USD contribution: ") or "0")
            break
        except ValueError:
            print("  Invalid input. Please enter a number.")
    
    contribution_chf_usd = contribution_chf * exchange_rates['CHF']
    total_contribution_usd = contribution_usd + contribution_chf_usd
    
    if total_contribution_usd != 0:
        action = "Adding" if total_contribution_usd > 0 else "Withdrawing"
        print(f"  {action} ${abs(total_contribution_usd):,.2f} USD total across all portfolios")
    
    return total_contribution_usd

def prompt_current_cash(exchange_rates, portfolio_name):
    """
    Ask for current cash holdings in CHF and USD.
    """
    print(f"\nCurrent cash holdings for {portfolio_name}:")
    
    while True:
        try:
            cash_chf = float(input(f"  {portfolio_name} current CHF: "))
            break
        except ValueError:
            print("  Invalid input. Please enter a number.")
    
    while True:
        try:
            cash_usd = float(input(f"  {portfolio_name} current USD: "))
            break
        except ValueError:
            print("  Invalid input. Please enter a number.")
    
    cash_chf_usd = cash_chf * exchange_rates['CHF']
    total_cash_usd = cash_usd + cash_chf_usd
    print(f"  Total current cash (USD) for {portfolio_name}: ${total_cash_usd:,.2f}")
    
    return total_cash_usd

def prompt_withdrawal(exchange_rates):
    """
    Ask the user for withdrawal amounts in CHF and USD, convert to USD using provided exchange rates.
    """
    while True:
        try:
            withdraw_chf = float(input("Enter amount to withdraw in CHF: "))
            break
        except ValueError:
            print("Invalid input. Please enter a number for CHF withdrawal.")
    while True:
        try:
            withdraw_usd = float(input("Enter amount to withdraw in USD: "))
            break
        except ValueError:
            print("Invalid input. Please enter a number for USD withdrawal.")
    withdraw_chf_usd = withdraw_chf * exchange_rates['CHF']
    total_withdraw_usd = withdraw_usd + withdraw_chf_usd
    print(f"\nWithdrawal in CHF converted to USD: ${withdraw_chf_usd:,.2f}")
    print(f"Withdrawal in USD: ${withdraw_usd:,.2f}")
    print(f"Total Withdrawal (USD): ${total_withdraw_usd:,.2f}\n")
    return total_withdraw_usd

def get_prices_usd(target_allocations, tickers_data, exchange_rates):
    """
    Retrieve current market prices for each ticker and convert to USD.
    """
    prices_usd = {}
    for ticker in target_allocations:
        data = tickers_data[ticker]
        # Use midpoint of bid/ask as current price, fallback to NAV
        if data.bid and data.ask and data.bid > 0 and data.ask > 0 and data.bid < data.ask:
            current_price = (data.bid + data.ask) / 2
        elif data.navPrice and data.navPrice > 0:
            current_price = data.navPrice
        else:
            raise ValueError(f"No valid price data for {ticker}")
        
        price_usd = current_price * exchange_rates[data.currency]
        print(f"Current price {ticker} is: ${current_price:.2f} {data.currency} (= ${price_usd:.2f} USD)")
        prices_usd[ticker] = price_usd
    return prices_usd

def print_current_status_with_cash(target_allocations, shares, prices_usd, cash_usd):
    """
    Print the current ETFs/ETCs positions and cash, with all values in USD.
    """
    current_values = {}
    invested_value = 0.0
    print("\nCurrent ETF Positions:")
    for ticker in target_allocations:
        value = shares[ticker] * prices_usd[ticker]
        current_values[ticker] = value
        invested_value += value
        print(f"  {ticker}: {shares[ticker]} shares * ${prices_usd[ticker]:.2f} = ${value:,.2f}")
    overall_portfolio = invested_value + cash_usd
    print(f"\nTotal Invested Value (ETFs/ETCs): ${invested_value:,.2f}")
    print(f"Cash: ${cash_usd:,.2f}")
    print(f"Overall Portfolio Value (ETFs/ETCs + Cash): ${overall_portfolio:,.2f}\n")
    
    print("ETFs/ETCs Allocation Percentages (based on Invested Value):")
    for ticker in target_allocations:
        current_pct = (current_values[ticker] / invested_value) * 100 if invested_value > 0 else 0
        target_pct = target_allocations[ticker] * 100
        print(f"  {ticker}: {current_pct:.2f}% (Target: {target_pct:.2f}%)")
    
    return current_values, invested_value



def mode_rebalance(target_allocations, shares, prices_usd, cash_usd, chf_allocation, exchange_rates, tickers_data):
    current_values, invested_value = print_current_status_with_cash(target_allocations, shares, prices_usd, cash_usd)
    
    overall_portfolio = invested_value + cash_usd
    print("\nSince the goal is to invest all available cash into ETFs, the overall portfolio to be allocated is:")
    print(f"  Overall Portfolio Value (ETFs + Cash): ${overall_portfolio:,.2f}\n")
    
    print("Rebalance Recommendations for ETFs/ETCs:")
    trade_shares = {}
    trade_dtos = []
    
    target_chf_usd = overall_portfolio * chf_allocation
    current_chf_usd = cash_usd
    current_chf_pct = (current_chf_usd / overall_portfolio) * 100 if overall_portfolio else 0
    target_chf_pct = chf_allocation * 100
    print(f"CHF Cash: From ${current_chf_usd:.2f} ({current_chf_pct:.2f}% of portfolio) to ${target_chf_usd:.2f} ({target_chf_pct:.2f}% of portfolio)")
    
    for ticker in target_allocations:
        target_value = overall_portfolio * target_allocations[ticker]
        current_value = current_values[ticker]
        difference_value = target_value - current_value
        share_price = prices_usd[ticker]
        difference_shares = difference_value / share_price
        trade_shares[ticker] = difference_shares
        current_pct = (current_value / overall_portfolio) * 100 if overall_portfolio else 0
        target_pct = target_allocations[ticker] * 100
        trade_dto = buy_sell(ticker, difference_shares, difference_value, exchange_rates, tickers_data)
        if trade_dto:
            trade_dtos.append(trade_dto)
        print(f"  {ticker}:")
        print(f"     Current Allocation: {current_pct:.2f}% | Target Allocation: {target_pct:.2f}%")
    
    print_sorted_trades(trade_dtos, exchange_rates)
    
    print("\nSimulated Final ETFs/ETCs Holdings (after reinvesting all cash):")
    final_holdings = {}
    final_values = {}
    final_invested_value = 0.0
    for ticker in target_allocations:
        final_holdings[ticker] = shares[ticker] + trade_shares[ticker]
        final_values[ticker] = final_holdings[ticker] * prices_usd[ticker]
        final_invested_value += final_values[ticker]
        pct = (final_values[ticker] / overall_portfolio) * 100 if overall_portfolio else 0
        target_pct = target_allocations[ticker] * 100
        print(f"  {ticker}: {final_holdings[ticker]:.4f} shares, Value: ${final_values[ticker]:,.2f} ({pct:.2f}%, Target: {target_pct:.2f}%)")
    
    remaining_cash_usd = overall_portfolio - final_invested_value
    target_chf_usd = overall_portfolio * chf_allocation
    
    print(f"\nFinal Invested ETFs/ETCs Value: ${final_invested_value:,.2f}")
    print(f"Remaining Cash (CHF): ${remaining_cash_usd:,.2f}")

    final_total = final_invested_value + remaining_cash_usd
    # POSTCONDITION: Too much withdrawn.
    if final_total < overall_portfolio:
        print(f"\nWARNING: Final total ${final_total:,.2f} is less than original portfolio ${overall_portfolio:,.2f}.")
        print("This indicates that too much cash was withdrawn compromising your strategy.")

    # POSTCONDITION: Check that final total equals original overall portfolio
    if abs(final_total - overall_portfolio) > 1e-2:
        print(f"\nWARNING: Final total ${final_total:,.2f} does not match original portfolio ${overall_portfolio:,.2f}")
    else:
        print(f"✓ VERIFICATION: Final total matches original portfolio value: ${overall_portfolio:,.2f}")
    # POSTCONDITION: Check that remaining cash equals CHF allocation
    if abs(remaining_cash_usd - target_chf_usd) > 1e-2:
        print(f"\nWARNING: Remaining cash ${remaining_cash_usd:,.2f} does not match CHF allocation ${target_chf_usd:,.2f}")
    else:
        print(f"✓ POSTCONDITION MET: Remaining cash matches CHF allocation: ${remaining_cash_usd:,.2f}")



def buy_sell(ticker, difference_shares, difference_value, exchange_rates, tickers_data):
    """Return TradeDTO for a given ticker with IBKR fee comparison."""
    if abs(difference_shares) < 1e-4:
        return None
    
    ticker_data = tickers_data[ticker]
    fullExchangeName = ticker_data.fullExchangeName
    bid, ask, navPrice = ticker_data.bid, ticker_data.ask, ticker_data.navPrice
    
    if bid and ask and bid > 0 and ask > 0 and bid < ask:
        spread_fee_in_exchange_currency = abs(difference_shares) * (ask - bid) / 2
    else:
        spread_fee_in_exchange_currency = 0
    
    if bid and ask and bid > 0 and ask > 0 and bid < ask and navPrice and navPrice > 0:
        mid_price = (bid + ask) / 2
        deviation_from_nav = abs(mid_price - navPrice) / navPrice
        if difference_shares > 0:
            nav_deviation_fee_in_exchange_currency = abs(difference_shares) * (ask - navPrice)
        else:
            nav_deviation_fee_in_exchange_currency = abs(difference_shares) * (navPrice - bid)
    else:
        deviation_from_nav = 0
        nav_deviation_fee_in_exchange_currency = 0
    
    abs_value = abs(difference_value)
    abs_shares = abs(difference_shares)
    whole_shares = int(abs_shares)
    fractional_part = abs_shares - whole_shares
    rounded_up_shares = whole_shares + (1 if fractional_part > 0 else 0)
    
    is_buy = difference_shares > 0
    warning_message = ""
    
    # Check for large deviation between market price and NAV
    if bid and ask and bid > 0 and ask > 0 and bid < ask and navPrice and navPrice > 0:
        mid_price = (bid + ask) / 2
        if abs(mid_price - navPrice) / navPrice > 0.01:  # 1% threshold
            nav_deviation_pct = (mid_price - navPrice) / navPrice * 100
            warning_message = f"WARNING: Large NAV deviation! Market price {mid_price:.4f} vs NAV {navPrice:.4f} ({nav_deviation_pct:+.2f}%)"
    
    if fullExchangeName in ("Swiss", "EBS"):
        abs_value_chf = abs_value / exchange_rates.get('CHF', 1.0)
        # Switzerland (CHF): https://www.interactivebrokers.co.uk/en/pricing/commissions-stocks-europe.php
        # EBS exchange fees for ETFs: https://www.interactivebrokers.co.uk/en/accounts/fees/EBS-StkeEtfFees.php?nhf=T
        # Assuming < 50M CHF monthly volume (first tier)

        def calculate_wholeshare_fees_ebs(shares, value_chf):
            assert shares == int(shares), "calculate_wholeshare_fees_ebs should only be called with whole shares"
            
            tiered_commission = max(1.5, value_chf * 0.0005)
            ebs_fee = min(150, max(0.5, 1.5 + value_chf * 0.0150))
            trade_reporting_fee = 0.01
            clearing_fee = 0.08
            tiered_total = tiered_commission + ebs_fee + clearing_fee + trade_reporting_fee

            fixed_commission = max(5.0, value_chf * 0.0005)
            return tiered_total, fixed_commission

        def calculate_fractional_fees_ebs(shares, value_chf):
            frac_tiered = max(1.5, value_chf * 0.0005)
            frac_fixed = max(1.5, value_chf * 0.0005)
            return frac_tiered, frac_fixed
        
        rounded_down_value_chf = whole_shares * (abs_value_chf / abs_shares) if whole_shares > 0 else 0
        exact_value_chf = abs_value_chf
        rounded_up_value_chf = rounded_up_shares * (abs_value_chf / abs_shares)
        
        if whole_shares > 0:
            rounded_down_tiered, rounded_down_fixed = calculate_wholeshare_fees_ebs(whole_shares, rounded_down_value_chf)
        else:
            rounded_down_tiered, rounded_down_fixed = 0, 0
        
        if fractional_part > 0:
            frac_tiered, frac_fixed = calculate_fractional_fees_ebs(fractional_part, fractional_part * (abs_value_chf / abs_shares))
            exact_tiered = rounded_down_tiered + frac_tiered
            exact_fixed = rounded_down_fixed + frac_fixed
        else:
            exact_tiered = rounded_down_tiered
            exact_fixed = rounded_down_fixed
        
        rounded_up_tiered, rounded_up_fixed = calculate_wholeshare_fees_ebs(rounded_up_shares, rounded_up_value_chf)
        
        return TradeDTO(
            ticker=ticker,
            is_buy=is_buy,
            currency="CHF",
            exchange=fullExchangeName,
            warning_message=warning_message,
            rounded_down=ShareTypeData(whole_shares, rounded_down_value_chf, rounded_down_tiered, rounded_down_fixed),
            exact=ShareTypeData(abs_shares, exact_value_chf, exact_tiered, exact_fixed),
            rounded_up=ShareTypeData(rounded_up_shares, rounded_up_value_chf, rounded_up_tiered, rounded_up_fixed),
            spread_fee=spread_fee_in_exchange_currency
        )
            
    elif fullExchangeName in ("NasdaqGM", "NYSEArca", "PCX", "NGM"):
        # https://www.interactivebrokers.co.uk/en/pricing/commissions-stocks.php?re=amer
        # https://www.interactivebrokers.co.uk/en/accounts/fees/ARCAstkfee.php?nhf=T
        def calculate_ibkr_fees_nysearca(shares, value):
            tiered_commission = max(0.35, shares * 0.0035)
            tiered_commission = min(tiered_commission, value * 0.01)
            
            fixed_commission = max(1.0, shares * 0.0050)
            fixed_commission = min(fixed_commission, value * 0.01)
            
            finra_trading_activity_fee = shares * 0.000166
            finra_audit_trail_fee = shares * 0.0000469  # using max range 0.000035 to 0.0000469
            regulatory_fees = finra_trading_activity_fee + finra_audit_trail_fee

            clearing_fee = min(value * 0.005, shares * 0.00020)
            nyse_pass_through = tiered_commission * 0.000175
            finra_pass_through = min(8.30, tiered_commission * 0.00056)
            arca_remove_liquidity = shares * 0.0030  # we pessimistically assume you remove liquidity as opposed to add.
            
            tiered_total = tiered_commission + regulatory_fees + clearing_fee + nyse_pass_through + finra_pass_through + arca_remove_liquidity
            fixed_total = fixed_commission + regulatory_fees
            
            return tiered_total, fixed_total
        
        rounded_down_value = whole_shares * (abs_value / abs_shares) if whole_shares > 0 else 0
        exact_value = abs_value
        rounded_up_value = rounded_up_shares * (abs_value / abs_shares)
        
        if whole_shares > 0:
            rounded_down_tiered, rounded_down_fixed = calculate_ibkr_fees_nysearca(whole_shares, rounded_down_value)
        else:
            rounded_down_tiered, rounded_down_fixed = 0, 0
        
        if fractional_part > 0:
            frac_tiered, frac_fixed = calculate_ibkr_fees_nysearca(fractional_part, fractional_part * (abs_value / abs_shares))
            exact_tiered = rounded_down_tiered + frac_tiered
            exact_fixed = rounded_down_fixed + frac_fixed
        else:
            exact_tiered = rounded_down_tiered
            exact_fixed = rounded_down_fixed
        
        rounded_up_tiered, rounded_up_fixed = calculate_ibkr_fees_nysearca(rounded_up_shares, rounded_up_value)
        
        return TradeDTO(
            ticker=ticker,
            is_buy=is_buy,
            currency="USD",
            exchange=fullExchangeName,
            warning_message=warning_message,
            rounded_down=ShareTypeData(whole_shares, rounded_down_value, rounded_down_tiered, rounded_down_fixed),
            exact=ShareTypeData(abs_shares, exact_value, exact_tiered, exact_fixed),
            rounded_up=ShareTypeData(rounded_up_shares, rounded_up_value, rounded_up_tiered, rounded_up_fixed),
            spread_fee=spread_fee_in_exchange_currency
        )
        
    elif fullExchangeName in ("XETRA", "GER"):
        # https://www.interactivebrokers.co.uk/en/pricing/commissions-stocks-europe.php
        # https://www.interactivebrokers.co.uk/en/accounts/fees/IBIS-StkFees.php?nhf=T
        abs_value_eur = abs_value / exchange_rates.get('EUR', 1.0)
        
        def calculate_fees_ibis(shares, value_eur):
            # Germany commission (assume ≤ €50M)
            tiered_commission = max(1.25, value_eur * 0.0005)
            tiered_commission = min(tiered_commission, 29.00)
            
            fixed_smartrouting = max(1.25 if shares != int(shares) else 3.00, value_eur * 0.0005)
            fixed_smartrouting = min(fixed_smartrouting, 29.00)
            
            exchange_fee_lean = min(36.00, value_eur * 0.000036)
            exchange_fee_standard = max(0.90, min(72.00, value_eur * 0.000072))
            
            clearing_fee_fixed = min(4.02, 0.02 + value_eur * 0.000008)
            clearing_fee_variable = min(4.00, value_eur * 0.000008)
            
            regulatory_fee = 0.01
            
            tiered_total = tiered_commission + exchange_fee_lean + clearing_fee_variable + regulatory_fee
            fixed_total = fixed_smartrouting + exchange_fee_standard + clearing_fee_fixed + regulatory_fee
            
            return tiered_total, fixed_total
        
        rounded_down_value_eur = whole_shares * (abs_value_eur / abs_shares) if whole_shares > 0 else 0
        exact_value_eur = abs_value_eur
        rounded_up_value_eur = rounded_up_shares * (abs_value_eur / abs_shares)
        
        if whole_shares > 0:
            rounded_down_tiered, rounded_down_fixed = calculate_fees_ibis(whole_shares, rounded_down_value_eur)
        else:
            rounded_down_tiered, rounded_down_fixed = 0, 0
        
        if fractional_part > 0:
            frac_tiered, frac_fixed = calculate_fees_ibis(fractional_part, fractional_part * (abs_value_eur / abs_shares))
            exact_tiered = rounded_down_tiered + frac_tiered
            exact_fixed = rounded_down_fixed + frac_fixed
        else:
            exact_tiered = rounded_down_tiered
            exact_fixed = rounded_down_fixed
        
        rounded_up_tiered, rounded_up_fixed = calculate_fees_ibis(rounded_up_shares, rounded_up_value_eur)
        
        return TradeDTO(
            ticker=ticker,
            is_buy=is_buy,
            currency="EUR",
            exchange=fullExchangeName,
            warning_message=warning_message,
            rounded_down=ShareTypeData(whole_shares, rounded_down_value_eur, rounded_down_tiered, rounded_down_fixed),
            exact=ShareTypeData(abs_shares, exact_value_eur, exact_tiered, exact_fixed),
            rounded_up=ShareTypeData(rounded_up_shares, rounded_up_value_eur, rounded_up_tiered, rounded_up_fixed),
            spread_fee=spread_fee_in_exchange_currency
        )
    elif fullExchangeName in ("Toronto", "TO"):
        # https://www.interactivebrokers.co.uk/en/pricing/commissions-stocks.php
        # https://www.interactivebrokers.co.uk/en/accounts/fees/TSXstkfee.php?nhf=T
        abs_value_cad = abs_value / exchange_rates.get('CAD', 1.0)
        
        def calculate_fees_tsx(shares, value_cad):
            # Assuming smallest volume tier (≤300k shares)
            tiered_commission = max(1.00, shares * 0.008)
            tiered_commission = min(tiered_commission, value_cad * 0.005)
            
            fixed_commission = max(1.00, shares * 0.01)
            fixed_commission = min(fixed_commission, value_cad * 0.005)
            
            exchange_fee = shares * 0.0017
            clearing_fee = min(2.00, shares * 0.00017)
            regulatory_fee = min(3.30, shares * 0.00011)
            
            tiered_total = tiered_commission + exchange_fee + clearing_fee + regulatory_fee
            fixed_total = fixed_commission
            
            return tiered_total, fixed_total
        
        rounded_down_value_cad = whole_shares * (abs_value_cad / abs_shares) if whole_shares > 0 else 0
        exact_value_cad = abs_value_cad
        rounded_up_value_cad = rounded_up_shares * (abs_value_cad / abs_shares)
        
        if whole_shares > 0:
            rounded_down_tiered, rounded_down_fixed = calculate_fees_tsx(whole_shares, rounded_down_value_cad)
        else:
            rounded_down_tiered, rounded_down_fixed = 0, 0
        
        if fractional_part > 0:
            frac_tiered, frac_fixed = calculate_fees_tsx(fractional_part, fractional_part * (abs_value_cad / abs_shares))
            exact_tiered = rounded_down_tiered + frac_tiered
            exact_fixed = rounded_down_fixed + frac_fixed
        else:
            exact_tiered = rounded_down_tiered
            exact_fixed = rounded_down_fixed
        
        rounded_up_tiered, rounded_up_fixed = calculate_fees_tsx(rounded_up_shares, rounded_up_value_cad)
        
        return TradeDTO(
            ticker=ticker,
            is_buy=is_buy,
            currency="CAD",
            exchange=fullExchangeName,
            warning_message=warning_message,
            rounded_down=ShareTypeData(whole_shares, rounded_down_value_cad, rounded_down_tiered, rounded_down_fixed),
            exact=ShareTypeData(abs_shares, exact_value_cad, exact_tiered, exact_fixed),
            rounded_up=ShareTypeData(rounded_up_shares, rounded_up_value_cad, rounded_up_tiered, rounded_up_fixed),
            spread_fee=spread_fee_in_exchange_currency
        )
    else:
        return TradeDTO(
            ticker=ticker,
            is_buy=is_buy,
            currency="USD",
            exchange=fullExchangeName,
            warning_message=f"TODO: {fullExchangeName} fees not implemented",
            rounded_down=ShareTypeData(whole_shares, abs_value, 0, 0),
            exact=ShareTypeData(abs_shares, abs_value, 0, 0),
            rounded_up=ShareTypeData(rounded_up_shares, abs_value, 0, 0),
            spread_fee=spread_fee_in_exchange_currency
        )

def print_sorted_trades(trades, exchange_rates):
    """Print trades sorted by pricing model preference, then by sell/buy order."""
    valid_trades = [trade for trade in trades if trade is not None]
    
    if not valid_trades:
        return
    
    def get_best_pricing_for_trade(trade):
        best_exact_tiered = trade.exact.tiered_fee
        best_exact_fixed = trade.exact.fixed_fee
        return "tiered" if best_exact_tiered < best_exact_fixed else "fixed"
    
    def sort_key(trade):
        pricing_preference = get_best_pricing_for_trade(trade)
        is_sell = not trade.is_buy
        return (pricing_preference == "fixed", is_sell, trade.ticker)
    
    sorted_trades = sorted(valid_trades, key=sort_key)
    
    current_pricing = None
    current_action_type = None
    total_fees_usd = 0
    
    for trade in sorted_trades:
        pricing_preference = get_best_pricing_for_trade(trade)
        action_type = "sell" if not trade.is_buy else "buy"
        
        if pricing_preference != current_pricing:
            print(f"\n{'='*60}")
            print(f"IBKR {pricing_preference.upper()} is cheaper:")
            print(f"{'='*60}")
            current_pricing = pricing_preference
            current_action_type = None
        
        if action_type != current_action_type:
            print(f"\n{action_type.upper()} orders:")
            print("-" * 20)
            current_action_type = action_type
        
        print_trade_details(trade)
        
        total_tiered = trade.exact.tiered_fee + trade.spread_fee
        total_fixed = trade.exact.fixed_fee + trade.spread_fee
        cheapest_total = min(total_tiered, total_fixed)
        
        fee_usd = cheapest_total * exchange_rates[trade.currency]
        total_fees_usd += fee_usd
    
    total_fees_chf = total_fees_usd / exchange_rates['CHF']
    
    print(f"\n{'='*60}")
    print("TOTAL TRANSACTION FEES:")
    print(f"{'='*60}")
    print(f"USD: ${total_fees_usd:.2f}")
    print(f"CHF: {total_fees_chf:.2f}")
    print(f"{'='*60}")

def print_trade_details(trade):
    """Print detailed information for a single trade."""
    action = "Buy" if trade.is_buy else "Sell"
    
    if trade.warning_message:
        print(f"  {trade.ticker}: {trade.warning_message}")
    
    print(f"  {trade.ticker}:")
    
    if trade.rounded_down.shares > 0:
        label = "exact shares" if trade.exact.shares == trade.rounded_down.shares else "rounded down shares"
        total_tiered = trade.rounded_down.tiered_fee + trade.spread_fee
        total_fixed = trade.rounded_down.fixed_fee + trade.spread_fee
        spread_suffix = f" + spread {trade.currency} {trade.spread_fee:.2f}" if trade.spread_fee > 0 else ""
        cheapest_total = min(total_tiered, total_fixed)
        print(f"    {action} {trade.rounded_down.shares:.0f} {label} ({trade.currency} {trade.rounded_down.value:.2f}) + IBKR tiered {trade.currency} {trade.rounded_down.tiered_fee:.2f} vs. IBKR fixed {trade.currency} {trade.rounded_down.fixed_fee:.2f}{spread_suffix} = cheapest total {trade.currency} {cheapest_total:.2f}")
    
    if trade.exact.shares != trade.rounded_down.shares:
        total_tiered = trade.exact.tiered_fee + trade.spread_fee
        total_fixed = trade.exact.fixed_fee + trade.spread_fee
        spread_suffix = f" + spread {trade.currency} {trade.spread_fee:.2f}" if trade.spread_fee > 0 else ""
        cheapest_total = min(total_tiered, total_fixed)
        print(f"    {action} {trade.exact.shares:.4f} exact shares ({trade.currency} {trade.exact.value:.2f}) + IBKR tiered {trade.currency} {trade.exact.tiered_fee:.2f} vs. IBKR fixed {trade.currency} {trade.exact.fixed_fee:.2f}{spread_suffix} = cheapest total {trade.currency} {cheapest_total:.2f}")
    
    if trade.rounded_up.shares > trade.exact.shares:
        total_tiered = trade.rounded_up.tiered_fee + trade.spread_fee
        total_fixed = trade.rounded_up.fixed_fee + trade.spread_fee
        spread_suffix = f" + spread {trade.currency} {trade.spread_fee:.2f}" if trade.spread_fee > 0 else ""
        cheapest_total = min(total_tiered, total_fixed)
        print(f"    {action} {trade.rounded_up.shares:.0f} rounded up shares ({trade.currency} {trade.rounded_up.value:.2f}) + IBKR tiered {trade.currency} {trade.rounded_up.tiered_fee:.2f} vs. IBKR fixed {trade.currency} {trade.rounded_up.fixed_fee:.2f}{spread_suffix} = cheapest total {trade.currency} {cheapest_total:.2f}")

def load_ticker_data(ticker_symbol):
    """Load ticker data and return TickerData object."""
    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        info = ticker_obj.info
        currency = info['currency']
        exchange = info['exchange']
        
        bid = info.get('bid')
        ask = info.get('ask')
        navPrice = info.get('navPrice')
        
        ticker_data = TickerData(
            symbol=ticker_symbol,
            currency=currency, 
            fullExchangeName=exchange,
            bid=bid,
            ask=ask,
            navPrice=navPrice,
            yf_object=ticker_obj
        )
        
        print(f"Loaded {ticker_symbol} ({exchange}): bid={bid}, ask={ask}, nav={navPrice} {currency}")
        
        return ticker_data
    except Exception as e:
        print(f"Error retrieving data for {ticker_symbol}: {e}")
        sys.exit(1)

def check_target_allocations(target_allocations):
    """Verify that the target allocations sum to 1."""
    total_alloc = sum(target_allocations.values())
    if abs(total_alloc - 1.0) > 1e-6:
        print(f"Error: Target allocations must sum to 1, but sum to {total_alloc:.2f}.")
        sys.exit(1)

def load_allocations_from_file(filepath):
    """Load allocations from JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data['allocations']
    except FileNotFoundError:
        print(f"Error: Allocation file '{filepath}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{filepath}'.")
        sys.exit(1)
    except KeyError:
        print(f"Error: Missing 'allocations' key in file '{filepath}'.")
        sys.exit(1)

def select_allocation(allocations):
    """Prompt user to select an allocation from available options."""
    print("\nAvailable allocations:")
    allocation_keys = list(allocations.keys())
    for i, key in enumerate(allocation_keys):
        allocation = allocations[key]
        print(f"  {i+1}. {allocation['name']} - {allocation['description']}")
    
    while True:
        try:
            choice = int(input("\nSelect allocation (enter number): "))
            if 1 <= choice <= len(allocation_keys):
                selected_key = allocation_keys[choice - 1]
                return selected_key, allocations[selected_key]
            else:
                print(f"Please enter a number between 1 and {len(allocation_keys)}")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main():
    parser = argparse.ArgumentParser(description='Portfolio rebalancing tool')
    parser.add_argument('-f', '--file', type=str, required=True,
                        help='Path to allocation JSON file')
    args = parser.parse_args()
    allocations = load_allocations_from_file(args.file)
    
    CURRENCY_CODES = {'CNY', 'JPY', 'GBP', 'AUD', 'CAD', 'INR', 'CHF', 'USD', 'EUR'}
    
    portfolios = []
    all_tickers = set()
    for portfolio_key, portfolio_data in allocations.items():
        if 'contribution_percentage' not in portfolio_data:
            print(f"Error: Portfolio '{portfolio_data['name']}' missing contribution_percentage")
            sys.exit(1)
        
        contribution_pct = portfolio_data['contribution_percentage']
        target_allocations = portfolio_data['holdings']
        
        check_target_allocations(target_allocations)
        
        cash_allocations = {k: v for k, v in target_allocations.items() if k in CURRENCY_CODES}
        ticker_holdings = {k: v for k, v in target_allocations.items() if k not in CURRENCY_CODES}
        
        portfolio = PortfolioDTO(
            key=portfolio_key,
            name=portfolio_data['name'],
            ticker_holdings=ticker_holdings,
            cash_allocations=cash_allocations,
            contribution_percentage=contribution_pct
        )
        portfolios.append(portfolio)
        all_tickers.update(ticker_holdings.keys())
    
    total_contribution = sum(p.contribution_percentage for p in portfolios)
    if abs(total_contribution - 1.0) > 1e-6:
        print(f"Error: Portfolio contribution percentages must sum to 1, but sum to {total_contribution:.4f}")
        sys.exit(1)

    tickers_data = {}
    for ticker_symbol in all_tickers:
        tickers_data[ticker_symbol] = load_ticker_data(ticker_symbol)

    exchange_rates = {}
    for currency in CURRENCY_CODES:
        if currency == 'USD':
            exchange_rates[currency] = 1.0
        else:
            rate_ticker = f"{currency}USD=X"
            rate = get_current_price(rate_ticker)
            if rate is None:
                print(f"Could not fetch exchange rate for {currency} to USD.")
                sys.exit(1)
            exchange_rates[currency] = rate
    
    print("Portfolio Manager")
    print("-----------------")
    
    total_cash_change_usd = prompt_cash_contributions(exchange_rates)
    
    for portfolio in portfolios:
        print(f"\n{'='*60}")
        print(f"Processing {portfolio.name}")
        print(f"{'='*60}")
        
        portfolio_cash_change = total_cash_change_usd * portfolio.contribution_percentage
        
        if portfolio_cash_change > 0:
            print(f"{portfolio.name} contribution: ${portfolio_cash_change:,.2f} ({portfolio.contribution_percentage*100:.1f}% of total contribution)")
        elif portfolio_cash_change < 0:
            print(f"{portfolio.name} withdrawal: ${abs(portfolio_cash_change):,.2f} ({portfolio.contribution_percentage*100:.1f}% of total withdrawal)")
        else:
            print(f"{portfolio.name}: No cash change")
        
        shares = prompt_holdings(portfolio.ticker_holdings, portfolio.name)
        current_cash_usd = prompt_current_cash(exchange_rates, portfolio.name)
        
        adjusted_cash_usd = current_cash_usd + portfolio_cash_change
        
        if portfolio_cash_change > 0:
            print(f"{portfolio.name} total cash after contribution: ${adjusted_cash_usd:,.2f}")
        elif portfolio_cash_change < 0:
            print(f"{portfolio.name} total cash after withdrawal: ${adjusted_cash_usd:,.2f}")
            print("(Note: Negative cash means ETFs/ETCs will be sold to generate the needed cash)")
        else:
            print(f"{portfolio.name} total cash: ${adjusted_cash_usd:,.2f}")
        
        prices_usd = get_prices_usd(portfolio.ticker_holdings, tickers_data, exchange_rates)
        
        chf_allocation = portfolio.cash_allocations.get('CHF', 0)
        mode_rebalance(portfolio.ticker_holdings, shares, prices_usd, adjusted_cash_usd, chf_allocation, exchange_rates, tickers_data)

if __name__ == '__main__':
    main()
