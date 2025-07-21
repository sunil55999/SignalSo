# SignalOS Desktop Frontend

Modern React/TypeScript dashboard for SignalOS desktop trading application.

## Features

- **Dark-themed Dashboard**: Modern trading interface optimized for desktop
- **Real-time System Health**: Live monitoring of all services and connections
- **Account Overview**: Balance, equity, margin, and risk metrics
- **Performance Tiles**: Win rate, trades executed, PnL, and execution speed
- **Activity Feed**: Real-time event timeline with filtering
- **Provider Management**: Signal source configuration and monitoring
- **Strategy Cards**: Trading rule management with backtesting
- **Risk Panel**: Live risk exposure and compliance monitoring
- **Quick Actions**: Import signals, add providers, run backtests, system controls

## Architecture

- **React 18** with TypeScript
- **Tailwind CSS** for styling with dark theme
- **Framer Motion** for animations
- **Radix UI** for accessible components
- **React Query** for API state management
- **React Router** for navigation
- **Recharts** for data visualization

## Development

```bash
cd desktop-app/frontend
npm install
npm run dev
```

The development server will start on port 3000 with proxy to Flask API on port 5000.

## Project Structure

```
src/
├── components/
│   ├── ui/              # Reusable UI components
│   ├── layout/          # Layout components (sidebar, header)
│   └── dashboard/       # Dashboard-specific components
├── pages/               # Route components
├── lib/                 # Utilities and API client
├── hooks/               # Custom React hooks
└── types/               # TypeScript type definitions
```

## Desktop Integration

- Optimized for desktop window resizing and full-screen
- Keyboard navigation and accessibility
- Native file dialogs for import/export
- Local storage for user preferences
- Real-time WebSocket connections for live data

## API Integration

All components connect to the Flask backend API:
- System status and health monitoring
- Signal and trade data
- Account information
- Real-time activity feed
- Provider and strategy management

## Components

### Core Layout
- `Layout.tsx` - Main application layout
- `SidebarNav.tsx` - Navigation sidebar
- `DashboardHeader.tsx` - Header with notifications and controls

### Dashboard Components
- `QuickActionsBar.tsx` - Primary action buttons
- `SystemHealthPanel.tsx` - Service status monitoring
- `AccountSummaryCard.tsx` - Account overview and license info
- `MetricsTiles.tsx` - Performance metrics grid
- `ActivityFeed.tsx` - Real-time event timeline
- `ProvidersWidget.tsx` - Signal provider management
- `StrategyCards.tsx` - Trading strategy overview
- `RiskPanel.tsx` - Risk management and compliance
- `NotificationDrawer.tsx` - Notification center

## Desktop-Specific Features

- Glass morphism design for modern desktop look
- Hover animations and transitions
- Responsive grid layout for various screen sizes
- Context menus and tooltips
- Desktop notification integration
- Local data persistence