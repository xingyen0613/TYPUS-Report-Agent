# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated report generation system for Typus Finance's weekly and monthly DeFi protocol reports. Reports are published to Medium and promoted via X (Twitter) Threads.

## Weekly Report Workflow (Primary)

Steps must run in order; later steps auto-trigger earlier ones if data is missing:

```
1. /fetch-sentio-data          ← Triggered manually, or auto-initiated when user requests report
                                   generation (e.g., "generate last week's report for Mar 9–15")
2. /weekly-report-prepare      ← Validates data, calculates metrics, generates charts + Data Brief
                                    ├── auto-triggers /fetch-market-prices (if weekly prices missing)
                                    └── auto-triggers /fetch-weekly-references (if market refs missing)
3. /weekly-report-generate     ← Writes Medium article + subtitles + X Threads
4. /convert-report-format      ← Converts Markdown → Medium-optimized HTML
5. /publish-medium             ← Playwright: creates Medium draft, uploads all PNGs to CDN
```

**After generating the report draft, ALWAYS proceed through all remaining steps** (HTML conversion → Medium publish → X Threads URL update) unless explicitly told to pause.

When user pastes back the published Medium URL, auto-update the LINK placeholder in the corresponding X Threads file.

## Monthly Report Workflow

```
1. /monthly-report-prepare     ← auto-triggers /fetch-typus-data and /fetch-weekly-references as needed
2. /monthly-report-generate    ← auto-triggers /fetch-market-prices if missing
3. /convert-report-format
4. /publish-medium
```

## Data Sources & File Naming

| Data | Directory | Naming Convention |
|------|-----------|-------------------|
| Sentio on-chain (weekly) | `data-sources/sentio-data/` | `week-{N}-{month}-{year}.md` |
| Weekly Data Brief | `data-sources/sentio-data/` | `week-{N}-{month}-{year}-brief.md` |
| Weekly prices | `data-sources/weekly-prices/` | `week-{N}-{month}-{year}.md` |
| Monthly prices | `data-sources/market-prices/` | `{month}-{year}.md` |
| Market references | `data-sources/weekly-references/` | `Week_DD Mon ~ DD Mon, YYYY.md` |
| Typus TVL/Users | `data-sources/typus-data/` | CSV files from Google Sheets |

**Output paths**: `outputs/weekly/draft/` → `outputs/weekly/final/` (same for monthly)

**Weekly References date rule**: Zerocap article title date minus 7 days = actual week's Monday. E.g., article "2 February 2026" → file `Week_26 Jan ~ 01 Feb, 2026.md`

## Skills Architecture

All skills live in `.claude/skills/` (local, takes priority over global skills). Edit `SKILL.md` in any skill directory to change behavior immediately.

Key implementation files:
- `.claude/skills/generate-charts/generate_charts.py` — generates TLP Price (~4 week history), Fee Breakdown, OI Distribution, Volume, DAU, PnL, Liquidation charts as PNG
- `.claude/skills/publish-medium/import-to-medium.js` — Playwright script; auto-uploads all PNGs in `outputs/weekly/final/` to Medium CDN, replaces `[Image: ...]` placeholders with CDN URLs
- `.claude/skills/fetch-sentio-data/.api-key` — Sentio API key (gitignored, one line)

Medium session cookies are stored at `~/.config/typus-medium-session.json` (outside repo, gitignored).

`/fetch-sentio-data` also supports **ad-hoc custom queries** beyond the 13 standard queries — when the user asks for specific on-chain data (e.g., volume for a token pair, top trades by fee, position history), Claude should use the custom query mode documented in the skill (reads `tables/` annotations → writes SQL → confirms with user → executes).

## TVL Calculation

System ignores the old TVL_Total column. Use:
- **Total TVL** = TVL_Perps + DOV TVL + SAFU TVL
- **Options TVL** = DOV TVL + SAFU TVL

## Data Presentation Rules

- OI, DAU, Trader P&L and other small absolute values: do NOT present raw numbers. Use WoW% or trend language instead.
- Weekly report: 600–800 word Medium article, no tables, narrative subtitles for each section.

## Report Structures

**Weekly (8 sections)**: Title → TL;DR (single paragraph) → Market Context → LP Performance → 30-Day Performance → Trader Performance → OI & Sentiment → Closing + CTA (`https://typus.finance/tlp/`)

**Monthly (10 points)**: Title → TL;DR → Market Pulse & TVL → Performance Deep Dive → User Engagement → Product Shipped → Roadmap Update → Community & Ecosystem → Building Momentum → CTA

**X Threads**: 1 hook + 4 numbered tweets (1/4…4/4), 200–280 chars each, no emoji except hook, last tweet contains Medium link placeholder.

## Maintenance

- Future optimization ideas → `OPTIMIZATION_ROADMAP.md`
- After successful new features or changes → update `OPTIMIZATION_ROADMAP.md` and `QUICKSTART.md`
