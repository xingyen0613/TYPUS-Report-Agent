# Typus TLP Weekly Report | February 2, 2026

## TL;DR

- **Perp relaunch's first full trading week** recorded ~$61k in volume with an average of 10 daily active users, establishing baseline activity as the platform enters its growth phase.
- **mTLP returned -5.89%**, driven primarily by SUI's -11.5% weekly decline impacting the asset basket, while counterparty gains from trader losses partially offset the drawdown.
- **iTLP-TYPUS returned +0.45%**, generating steady yield from fee income and counterparty gains.
- **Traders realized -$465 in losses**, concentrated on Thursday's market crash, with $575 in total liquidations — translating directly into LP counterparty revenue.

---

## Market Context & Volume

The broader crypto market faced significant headwinds this week, with all major assets posting losses. Bitcoin declined -7.7% ($76,907 to $71,010), Ethereum fell -7.1%, and altcoins saw steeper corrections — SOL dropped -13.7% and SUI declined -11.5% ($1.10 to $0.98).

The week's defining moment came on Thursday (Feb 5), when a sharp sell-off sent BTC down as much as -12.6% and SUI -17.2% intraday. A strong recovery followed on Friday, but most assets closed the week well below their opening levels.

[Image: Weekly Volume Chart]

**Platform Activity**

As the first complete trading week since the Perp relaunch, the platform recorded ~$61k in total volume, averaging ~$8.8k per day. While modest in absolute terms, this represents the initial baseline for the relaunched product. Notably, TLP saw net inflows throughout the week with near-zero outflows, signaling early LP confidence.

Daily active users averaged 10, with a clear uptick during high-volatility periods — DAU peaked at 19 on Thursday (Feb 5) during the market sell-off, suggesting traders are actively engaging the platform during meaningful market moves.

[Image: DAU Chart]

**Volume by Token**

| Token | Volume | Share | L/S Ratio |
|-------|--------|-------|-----------|
| SUI | ~$46k | 79% | 4.48 (Long-heavy) |
| BTC | ~$7.5k | 13% | 1.02 (Balanced) |
| TYPUS | ~$3.1k | 5% | 2.37 (Long-leaning) |
| XAU | ~$915 | 2% | Short only |
| SOL | ~$608 | 1% | Short only |

SUI dominated trading activity at 79% of total volume, with a pronounced long bias (L/S ratio 4.48). BTC was the second most traded pair with a near-balanced long/short ratio of 1.02. Interestingly, SOL and XAU saw exclusively short-side activity, while HYPE (~$495) was traded exclusively long.

---

## LP Performance

### mTLP: -5.89%

mTLP's weekly return was driven almost entirely by the asset basket effect, as the underlying SUI exposure (-11.5%) weighed heavily on pool value.

**Return Attribution:**
- **Basket Effect (SUI price):** -6.66% — the dominant factor, reflecting SUI's decline within mTLP's asset composition
- **Counterparty PnL:** +0.76% — traders' net realized loss of $465 flowed directly to LPs as counterparty revenue
- **Fee Income:** +0.01% — TLP fees of $47.48 contributed marginally given the pool's TVL

The counterparty gain partially cushioned the basket drawdown, but at this stage of platform growth, fee income and counterparty revenue are naturally small relative to the asset price impact on the pool.

[Image: TLP Price Chart]

### iTLP-TYPUS: +0.45%

iTLP-TYPUS delivered a positive return, with contributions from both fee income (+0.14%) and counterparty gains (+0.31%). As a pool composed entirely of USDC providing liquidity solely for the TYPUS/USD pair, its returns are independent of broader crypto price movements.

[Image: Fee Breakdown]

---

## iTLP-TYPUS vs mTLP vs SUI: 30-Day Performance Deep Dive

With only one week of data since the Perp relaunch, a full 30-day performance comparison is not yet available. This section will be populated as the platform accumulates additional weekly data points (minimum 4 weeks required for meaningful Sharpe Ratio calculations).

**Week 1 Snapshot:**

| Product | Week 1 Return | Risk Profile |
|---------|--------------|--------------|
| iTLP-TYPUS | +0.45% | Low — USDC-denominated, no crypto price exposure |
| mTLP | -5.89% | Medium — exposed to SUI price via asset basket |
| SUI (spot) | -11.5% | High — direct token price exposure |

mTLP's -5.89% return compares favorably to SUI's -11.5% spot decline, as the fee income and counterparty revenue components provided partial offset. This dynamic — where LP returns dampen underlying asset volatility — is a core feature of the mTLP structure.

[Image: 30-Day Comparison Chart]

---

## Trader Performance

Traders realized a net loss of -$465 for the week, with the vast majority concentrated on a single day.

| Day | Realized PnL | Liquidation |
|-----|-------------|-------------|
| Mon 2/2 | -$2.25 | $0 |
| Tue 2/3 | -$4.05 | $20 |
| Wed 2/4 | -$4.71 | $45 |
| **Thu 2/5** | **-$364.56** | **$256** |
| Fri 2/6 | -$98.06 | $113 |
| Sat 2/7 | +$2.64 | $141 |
| Sun 2/8 | +$6.46 | $0 |

Thursday's market crash accounted for 78% of the week's total trader losses (-$365 of -$465), directly correlating with BTC's -12.6% and SUI's -17.2% intraday moves. Liquidations totaled $575 for the week, concentrated between Thursday and Saturday as positions were unwound during elevated volatility.

From the LP perspective, these trader losses translated into +0.76% counterparty return for mTLP — a meaningful positive contribution that partially offset the basket drawdown.

[Image: Daily PnL Chart]

[Image: Liquidation Chart]

---

## Open Interest & Sentiment

Total open interest stood at ~$12.2k at week's end, with a net long bias (L/S ratio 1.45).

| Token | OI | L/S Ratio | Net Exposure | Trader Unrealized PnL |
|-------|----|-----------|--------------|-----------------------|
| SUI | $11,500 (94%) | 1.50 | +$2,293 Net Long | +$660 |
| XAU | $226 | Net Long | +$226 | -$0.37 |
| BTC | $220 | 0.28 | -$124 Net Short | +$2.82 |
| WAL | $152 | 0.07 | -$133 Net Short | +$7.32 |

SUI accounts for 94% of all open interest, reflecting its dominant role on the platform. The net long positioning (+$2,293) indicates traders are positioning for a SUI recovery following this week's decline.

Traders currently hold +$653 in unrealized profit across all positions (primarily from SUI longs), which represents an equivalent unrealized loss for TLP. This exposure will be a key metric to monitor in the coming week — if SUI continues to decline, these unrealized gains could reverse, benefiting LPs.

[Image: OI Distribution]

---

## Conclusion

This first full week of trading since the Perp relaunch established a solid operational baseline. Despite facing an unfavorable market environment with broad crypto declines, the platform demonstrated organic engagement — DAU surged during high-volatility moments, TLP saw consistent net inflows with near-zero outflows, and all core trading functions operated smoothly.

mTLP's -5.89% return was predominantly a function of SUI's -11.5% decline — the fee and counterparty components contributed positively but are naturally modest at this stage of platform growth. As volume scales, these revenue streams will play an increasingly meaningful role in LP returns.

Looking ahead, Typus has launched a **70% trading fee discount** effective February 10, a direct response to community feedback aimed at fostering a more competitive trading environment during this growth phase. This initiative is expected to support volume growth and improve the trading experience as the platform builds its user base.

---

Earn real yield: https://typus.finance/tlp/
Follow us: https://x.com/TypusFinance
