<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# SignalOS Dashboard Page Development Guide for AI Agent

## 1. Use the Recommended Language \& Stack

- **Language:** TypeScript
- **Framework:** React (18+)
- **Styling:** Tailwind CSS (or similar utility-first, responsive CSS)
- **UI Library:** Shadcn UI, Material UI, or Blueprint for advanced dashboard widgets
- **State Management:** Zustand
- **Data Fetching:** TanStack/React Query
- **Packaging:** Tauri (for lightweight, secure desktop `.exe` builds)


## 2. Core Dashboard Layout Structure

### Main Regions

| Region | Description |
| :-- | :-- |
| Top Bar/Header | Brand, account summary, quick actions, notifications |
| Sidebar | Main navigation (Dashboard, Providers, Strategies, etc.) |
| Main Content | Dashboard: all critical metrics, controls, analytics |
| Notification Hub | Alerts, errors, and user messages |

## 3. Essential Dashboard Page Components

### A. Account \& System Overview

- **Account Summary Card:**
    - Balance
    - Equity
    - Margin
    - Open PnL
    - License/tier status
- **System Health Indicators:**
    - AI Parser
    - MT5 Bridge
    - Telegram Link
    - Marketplace
    - Notifications
    - Each status should have dynamic badges (green/yellow/red) and show tooltips with connection details.
- **Session/License Audit:**
    - Connected user/device, license state, validity check


### B. Quick Actions Bar

- **Buttons (always visible at top or floating):**
    - Import Signals
    - Backtest Strategy
    - Pause/Resume Automation
    - Add/Connect Provider
    - Help/Documentation
    - Dashboard Settings


### C. Performance Metrics \& Trend Snapshots

- **Smart Metrics Tiles:**
    - Today’s PnL
    - Win Rate
    - Trades Executed
    - Parsing Success %
    - Execution Speed/Latency (ms)
- **Trend Charts:**
    - Equity curve (mini-chart)
    - Monthly/weekly PnL bar chart
    - Win rate per provider (selectable/switchable)


### D. Interactive Activity Feed

- **Live Timeline/Log:**
    - Shows real-time events: trades, signals parsed, warnings, errors, system status changes
    - Filter by type: All, Trades, Errors, System, Providers, Signals
    - Click any item for a details modal or side drawer with:
        - Full event detail (input/output/latency/results)
        - "Retry"/"Acknowledge"/"Ignore" buttons for errors

---

### E. Provider \& Strategy Summaries

- **Providers Table/Widget:**
    - Provider/channel name
    - Status (active/inactive/error)
    - Recent performance (PnL, win%, latency)
    - “Test” button for simulated trade or parsing
- **Strategy Cards:**
    - Active strategies summary: title, main rule, assigned providers
    - “Simulate/Backtest” and “Edit” buttons


### F. Risk \& Compliance Panel

- **Live Risk Display:**
    - Exposure by symbol/provider (bar/heatmap)
    - Open trades, margin, PnL
    - Prop-firm compliance or risk warnings
    - Visual alerts if risk limits/margin are approached

---

### G. Notification \& Support Center

- **Unified Notification List:**
    - Warnings
    - Errors
    - Success/info messages
    - "Resolve"/"Fix Now"/"Dismiss" buttons
- **Onboarding/Help Banner:**
    - Wizard or banner for first-time setup, “Show how” button


### H. Additional User Experience Features

- **Customization:**
    - Pin, hide, or reorder dashboard widgets for personalization
- **Accessibility:**
    - High-contrast toggle, keyboard navigation, tooltip explanations
- **Export:**
    - CSV/PDF export for metrics, logs, and analytics


## 4. All Dashboard Functions/Buttons Required

| Function/Button | Purpose |
| :-- | :-- |
| Import Signals | Start the import workflow for CSV/JSON/PDF signals |
| Backtest Strategy | Launch strategy backtesting modal or page |
| Pause/Resume Automation | Toggle all live automation on/off instantly |
| Add Provider | Quick-add new signal provider or Telegram channel |
| Help/Docs | Open documentation; guided help |
| Dashboard Settings | Access user, theme, data, and licensing settings |
| View Trade/Signal Details | Drilldown any log entry or metric |
| Test Provider Parsing | Run test parse or simulation on selected provider |
| Simulate/Backtest Strategy | Test selected strategy on recent/historic signals |
| Edit Strategy | Open builder/editor for quick modifications |
| Pin/Hide/Move Widget | Customize dashboard layout |
| Fix/Retry/Ignore Errors | Context menu actions on event log/alerts |
| Dismiss Notification | Remove resolved notification or message |
| Export Data | Download logs/reports in supported formats |
| Toggle High Contrast | Accessibility setting |

## 5. Implementation Notes

- Construct each dashboard region as a modular React component with props/state managed via Zustand.
- Fetch/update data regularly (2–5s polling or WebSocket) for every live panel.
- All buttons should have loading, error, and disabled states.
- Backend endpoint for each action must be mapped/tested (refer to API docs).
- Use Tailwind and the chosen UI library for a clean, modern, responsive look.
- Provide a design doc (Figma/Storybook) documenting every widget, button, and workflow before start of code.
- Begin with mock data; wire up live backend only after UI/UX sign-off.

**Result:**
Following this guide, the AI agent will produce a SignalOS dashboard that is more usable, actionable, and professional than current market leaders, ensuring every function, control, and metric is represented, discoverable, and user-driven.

