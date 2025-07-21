<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# SignalOS Dashboard Page: Comprehensive Desktop App UI Specification

> **Note:**
> This guide describes the structure and features for the Dashboard page **specifically developed for the SignalOS desktop application**. All code, components, and files referenced must reside within `desktop-app/frontend/`—the official frontend directory for your cross-platform desktop app (packaged as `.exe`, `.dmg`, etc. via Tauri/Electron).

## 1. Layout \& Structure

### Main Desktop Layout

- **Persistent Sidebar Navigation**
    - Fixed on the left; clear dark themed design.
    - Sections: Dashboard (active), Providers, Strategies, Trades, Backtest, Logs, Settings, Help.
    - Animated icons, contrast highlights for selected section.
    - Responsive for small desktop screens (compact/expand).
- **Header Bar**
    - Left: Desktop app logo, SignalOS name.
    - Center: Page title (e.g., "Dashboard – Mission Control").
    - Right: User avatar/profile, notifications (with animation if unread), quick theme toggle.
- **Main Content Grid**
    - Multi-column flexible grid: all desktop-focused cards and widgets.
    - Designed for desktop window resizing/full screen.


## 2. Dashboard Card Components

### Account \& License Overview

- Top summary card showing:
    - Account name, license/tier badge (desktop key/plan)
    - Balance, equity, margin, open PnL
    - “Desktop-Activated” status indicator
    - Click to expand for local/desktop app config


### System Health Bar

- Real-time service status row:
    - AI Parser (status)
    - MT5 Bridge (desktop/local)
    - Telegram/Provider API
    - Marketplace (plugin support)
    - Notifications/connection (with animated pulses)
- Tooltip diagnostics optimized for desktop popovers


### Quick Actions Bar

- Floating/sticky or header-integrated:
    - Import Signals (desktop native file dialog/modal)
    - Add Provider/Channel
    - Run Backtest
    - Pause/Resume Automation (toggle, visible always)
    - Help/Docs (desktop-specific guides)


### Performance \& Trend Tiles

- Win Rate, Trades Executed, Today's PnL, Signal Parsing %, Execution Speed (ms)
- Mini equity curve, Win Rate by provider (all with animated charts for desktop)
- Tooltips designed for mouse/keyboard navigation


## 3. Live Activity/Event Timeline

- Real-time event feed, fully interactive:
    - Desktop pop-out log window supported
    - Drag-to-expand/feed resizing for power users
    - Filters: All, Trades, Errors, Providers, Parsing, System
    - Click items for modal/drawer with details, retry/fix/acknowledge actions


## 4. Providers \& Strategies Widgets

- Inline Providers Table/Widget:
    - Provider logo/name, type, status
    - Last signal received, recent performance
    - Quick: Test Parse, Edit, Pause (optimized for mouse actions)
- Active Strategies Cards
    - Main rule summary, assigned providers, last backtest
    - Edit, simulate/backtest in-place


## 5. Risk \& Compliance Panel

- Live risk exposure by symbol or provider
- Margin bar, drawdown, account compliance (prop firm rules)
- Visual progress/risk meters; warnings highlighted for desktop UX


## 6. Centralized Notification/Onboarding Center

- Drawer or popup for all alerts, errors, info (desktop notifications optionally integrated)
- “Getting Started” coach marks for first time use or updates
- Actionable: “Fix now”, “Learn more”, “Dismiss”


## 7. Customization \& Accessibility (Desktop-Specific)

- Panel drag, pin, hide/rearrange (stored locally per user profile)
- Keyboard navigation, focus rings, screen reader and high-contrast themes
- Dockable panels for widescreen desktop layouts


## 8. Integration \& Feedback Mechanisms

- All controls mapped to backend API endpoints (real-time via polling/WebSocket)
- Desktop specific loading states, error toasts, and offline indicators
- Immediate feedback for all user actions (import, trade, test, pause)


## 9. Example Component Map

| Component Name | Functionality |
| :-- | :-- |
| DashboardHeader.tsx | Top bar, logo, profile, notifications |
| SidebarNav.tsx | Desktop navigation for all app sections |
| QuickActionsBar.tsx | Import, Add, Backtest, Pause, Help |
| SystemHealthPanel.tsx | Desktop-focused service/connection statuses |
| AccountSummaryCard.tsx | Balance, equity, license, desktop status |
| MetricsTiles.tsx | Animated desktop metrics and mini-charts |
| ActivityFeed.tsx | Live timeline, desktop popout support |
| ProvidersWidget.tsx | Providers summary with mouse-optimized actions |
| StrategyCards.tsx | Live strategies, quick edit/backtest buttons |
| RiskPanel.tsx | Visual risk exposure/compliance gauges |
| NotificationDrawer.tsx | Central alerts, onboarding, desktop badges |

## 10. Backend \& App Integration

- All dashboard components fetch and present data from desktop-app backend endpoints.
- File dialogs, notifications, and advanced import/export use desktop-native APIs where needed.
- Real-time updates ensure dashboard reflects actual local backend/trading state.


## 11. Testing \& Validation

- Test with desktop app window resizing, drag-to-expand, high-DPI scaling.
- Keyboard navigation and accessibility for all interactive widgets
- Desktop-focused notifications, error recovery, and offline indicators.


## 12. Development Checklist

- [ ] All dashboard UI code under `desktop-app/frontend/`
- [ ] Modern, modular, and fully dark-themed layout
- [ ] Desktop-optimized feedback, navigation, dialogs, and help
- [ ] Responsive to real-time local/remote backend state, with robust error handling

**This step-by-step guide ensures the SignalOS Dashboard for the desktop app is robust, modern, visually engaging, and optimized for both trading power users and newcomers. Develop all features and components as specified for a desktop environment in `desktop-app/frontend/` for seamless integration and packaging.**

