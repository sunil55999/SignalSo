
# SignalOS Web Dashboard - Complete UI Documentation

## 📋 Overview

The SignalOS Web Dashboard is a modern React-based interface built with TypeScript, Tailwind CSS, and Radix UI components. It provides comprehensive monitoring, control, and configuration capabilities for the trading automation system.

## 🏗️ UI Architecture

### Technology Stack
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with custom design system
- **Components**: Radix UI primitives
- **Icons**: Lucide React icons
- **Charts**: Recharts for data visualization
- **State Management**: TanStack Query for server state
- **Routing**: Wouter for client-side navigation

### Design System
- **Color Palette**: Modern gray scale with brand colors
- **Typography**: System fonts with hierarchical sizing
- **Spacing**: Consistent 8px grid system
- **Shadows**: Subtle elevation shadows
- **Borders**: Rounded corners with consistent radius

## 🎨 Main Layout Structure

### MainLayout Component (`layouts/MainLayout.tsx`)
- **Top Header**: User navigation and system status
- **Sidebar**: Main navigation menu
- **Content Area**: Dynamic page content
- **Toast Notifications**: Global notification system

### Responsive Design
- **Mobile-First**: Progressive enhancement for larger screens
- **Breakpoints**: sm (640px), md (768px), lg (1024px), xl (1280px)
- **Navigation**: Collapsible sidebar on mobile devices

## 📄 Core Pages & Components

### 1. Dashboard Page (`pages/dashboard.tsx`)

#### ModernStatsGrid (`components/dashboard/ModernStatsGrid.tsx`)
- **Live Account Balance**: Real-time balance display with profit/loss indicators
- **Active Trades Counter**: Current open positions with status colors
- **Today's Performance**: Daily P&L with percentage change
- **Signal Success Rate**: Win/loss ratio with visual indicators
- **Monthly Performance**: Monthly statistics with trend arrows
- **Risk Level Indicator**: Current risk exposure with color coding

#### PerformanceChart (`components/charts/PerformanceChart.tsx`)
- **Interactive Line Chart**: Profit/loss over time
- **Time Range Selectors**: 1D, 7D, 30D, 90D, 1Y options
- **Tooltip Data**: Hover details with exact values
- **Responsive Design**: Adapts to container size

#### ModernLiveTrades (`components/dashboard/ModernLiveTrades.tsx`)
- **Trade List**: Current open positions
- **Trade Cards**: Individual trade information
  - Symbol and direction (BUY/SELL)
  - Entry price and current price
  - Profit/loss with color indicators
  - Lot size and trade time
- **Real-time Updates**: Live price and P&L updates
- **Action Buttons**: Close trade, modify SL/TP

#### QuickActions (`components/dashboard/quick-actions.tsx`)
- **Emergency Stop**: Immediate halt of all trading
  - Red warning button with confirmation dialog
  - Square icon with loading state
- **Pause/Resume Trading**: Toggle signal processing
  - Amber pause button / Green resume button
  - Play/Pause icons with status indicator
- **Stealth Mode Toggle**: Hide/show SL/TP in MT5
  - Purple enabled state / Gray disabled state
  - Eye/EyeOff icons with status dot
- **Desktop Sync**: Force synchronization
  - Blue sync button with refresh icon
  - Loading spinner during sync

#### DesktopAppStatus (`components/desktop/DesktopAppStatus.tsx`)
- **Connection Status**: MT5 and desktop app connectivity
- **Last Sync Time**: Time since last synchronization
- **Health Indicators**: System component status
- **Quick Stats**: Brief performance metrics

### 2. Signals Page (`pages/signals-page.tsx`)

#### SignalTable (`components/tables/SignalTable.tsx`)
- **Signal History**: Comprehensive signal listing
- **Columns**:
  - Timestamp with relative time
  - Provider name with trust score
  - Symbol and direction
  - Entry price and targets
  - Status (Executed, Pending, Rejected)
  - Confidence score with color coding
  - Actions (View details, Replay)
- **Filtering**: Date range, provider, symbol, status
- **Sorting**: All columns sortable
- **Pagination**: Server-side pagination with page size options

### 3. Strategy Builder (`components/modals/ModernStrategyBuilder.tsx`)

#### Strategy Blocks
- **Time Window Block** (`components/strategy-blocks/TimeWindowBlock.tsx`)
  - Start/end time selectors
  - Timezone configuration
  - Weekend trading toggle
  
- **Risk Management Block** (`components/strategy-blocks/RiskManagementBlock.tsx`)
  - Maximum lot size slider
  - Risk percentage input
  - Maximum daily trades limit
  
- **Margin Filter Block** (`components/strategy-blocks/MarginFilterBlock.tsx`)
  - Margin threshold percentage
  - Emergency threshold setting
  - Action selection (Block/Reduce/Warning)
  
- **Keyword Filter Block** (`components/strategy-blocks/KeywordFilterBlock.tsx`)
  - Whitelist/blacklist keywords
  - Case-sensitive toggle
  - Regular expression support
  
- **Risk/Reward Block** (`components/strategy-blocks/RiskRewardBlock.tsx`)
  - Minimum R:R ratio
  - Maximum R:R ratio
  - Auto-adjustment options
  
- **Trailing Stop Block** (`components/strategy-blocks/TrailingStopBlock.tsx`)
  - Activation distance
  - Trail distance
  - Step size configuration

#### Visual Builder Interface
- **Drag & Drop**: Reorder strategy blocks
- **Add Block Button**: Dropdown with available blocks
- **Block Configuration**: Inline editing with validation
- **Strategy Preview**: Live strategy logic display
- **Save/Load**: Strategy templates and presets

### 4. Provider Management (`pages/providers-page.tsx`)

#### ProviderStatsCard (`components/providers/ProviderStatsCard.tsx`)
- **Provider Name**: Display name with status indicator
- **Trust Score**: Color-coded score with trend arrow
- **Performance Metrics**:
  - Win rate percentage
  - Average profit per trade
  - Total signals processed
  - Success rate over time periods
- **Action Buttons**: Enable/Disable, Configure, View Details

#### Provider Configuration
- **Signal Limits**: Hourly and daily limits
- **Weight Settings**: Provider priority weighting
- **Risk Parameters**: Provider-specific risk settings
- **Notification Settings**: Alert preferences

### 5. Analytics Page (`pages/Analytics.tsx`)

#### AnalyticsProviderTable (`components/analytics/AnalyticsProviderTable.tsx`)
- **Comprehensive Metrics**: Detailed provider performance
- **Time Range Filters**: Custom date range selection
- **Export Options**: CSV, PDF report generation
- **Comparison Tools**: Side-by-side provider comparison

### 6. Settings & Configuration Pages

#### Risk Management (`pages/risk-page.tsx`)
- **Global Risk Settings**: Account-wide risk parameters
- **Symbol-Specific Limits**: Per-symbol risk configuration
- **Emergency Controls**: Margin call and stop-out levels
- **Notification Preferences**: Risk alert settings

#### MT5 Configuration
- **Connection Settings**: Server, login, password
- **Trading Parameters**: Magic number, slippage, execution mode
- **Symbol Mapping**: Broker-specific symbol conversion
- **Spread Limits**: Maximum allowed spreads

## 🎨 UI Components Library

### Form Components
- **Input**: Text, number, password inputs with validation
- **Select**: Dropdown selectors with search
- **Checkbox**: Toggle switches with labels
- **Radio Group**: Single selection from options
- **Slider**: Numerical range selection
- **TextArea**: Multi-line text input

### Data Display
- **Card**: Content containers with headers and footers
- **Badge**: Status indicators with color coding
- **Avatar**: User profile images with fallbacks
- **Progress**: Loading and completion indicators
- **Skeleton**: Loading placeholders

### Navigation
- **Button**: Primary, secondary, outline, ghost variants
- **Breadcrumb**: Navigation path indicators
- **Tabs**: Content section navigation
- **Pagination**: Page navigation controls

### Feedback
- **Toast**: Temporary notification messages
- **Alert**: Persistent status messages
- **Dialog**: Modal confirmation dialogs
- **Tooltip**: Hover information displays

### Charts & Visualization
- **Line Charts**: Performance over time
- **Bar Charts**: Comparative data display
- **Pie Charts**: Proportion visualization
- **Area Charts**: Volume and trend display

## 🔧 Interactive Features

### Real-Time Updates
- **WebSocket Integration**: Live data streaming
- **Auto-Refresh**: Periodic data updates
- **Connection Status**: Real-time connectivity indicators
- **Error Handling**: Graceful degradation on connection loss

### User Interactions
- **Click Actions**: Primary interactions with feedback
- **Hover Effects**: Visual state changes
- **Loading States**: Activity indicators during operations
- **Confirmation Dialogs**: Safety checks for destructive actions

### Keyboard Navigation
- **Tab Navigation**: Accessible keyboard navigation
- **Keyboard Shortcuts**: Quick action hotkeys
- **Focus Management**: Logical focus order

## 📱 Mobile Responsiveness

### Adaptive Layouts
- **Collapsible Sidebar**: Mobile-friendly navigation
- **Responsive Grid**: Adaptive column layouts
- **Touch-Friendly**: Larger touch targets on mobile
- **Scroll Optimization**: Smooth scrolling experiences

### Mobile-Specific Features
- **Swipe Actions**: Touch gesture support
- **Pull-to-Refresh**: Manual refresh capability
- **Infinite Scroll**: Progressive content loading

## 🎯 Accessibility Features

### WCAG Compliance
- **Semantic HTML**: Proper element usage
- **ARIA Labels**: Screen reader support
- **Color Contrast**: Adequate contrast ratios
- **Focus Indicators**: Visible focus states

### Assistive Technology
- **Screen Reader Support**: Proper announcements
- **Keyboard Navigation**: Full keyboard accessibility
- **Alternative Text**: Image descriptions
- **Error Messages**: Clear validation feedback

## 🎨 Theme & Customization

### Color System
- **Primary Colors**: Brand identity colors
- **Semantic Colors**: Success, warning, error states
- **Neutral Grays**: Background and text colors
- **Opacity Variants**: Semi-transparent overlays

### Dark Mode Support
- **Theme Toggle**: User preference selection
- **Consistent Styling**: Coherent dark theme
- **System Integration**: Follows OS preference

## 🔍 Search & Filtering

### Global Search
- **Quick Search**: Instant results across all data
- **Search Suggestions**: Auto-complete functionality
- **Recent Searches**: Search history tracking

### Advanced Filters
- **Multi-Criteria**: Complex filtering options
- **Date Ranges**: Time-based filtering
- **Custom Filters**: User-defined filter sets
- **Filter Persistence**: Saved filter preferences

## 📊 Data Tables

### Advanced Table Features
- **Sorting**: Multi-column sorting capabilities
- **Filtering**: Column-specific filters
- **Pagination**: Efficient data loading
- **Column Customization**: Show/hide columns
- **Export Options**: Data export functionality

### Table Actions
- **Bulk Actions**: Multi-row operations
- **Inline Editing**: Direct data modification
- **Row Actions**: Individual row operations
- **Context Menus**: Right-click actions
