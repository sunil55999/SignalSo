
# SignalOS Project Structure

## 📋 Project Overview
SignalOS is an automated trading platform that parses Telegram signals, executes trades on MT5, and provides real-time monitoring through a web dashboard.

## 🏗️ Architecture
- **Frontend**: React + TypeScript with Vite
- **Backend**: Express.js with TypeScript
- **Database**: PostgreSQL with Drizzle ORM
- **Real-time**: WebSocket connections
- **Authentication**: JWT-based sessions
- **Desktop Integration**: Python modules for MT5 integration

## 📁 Directory Structure

```
signalos/
├── 📁 client/                          # Frontend React Application
│   ├── 📁 src/
│   │   ├── 📁 components/
│   │   │   ├── 📁 dashboard/           # Dashboard-specific components
│   │   │   │   ├── live-trades.tsx     # Real-time trade monitoring
│   │   │   │   ├── quick-actions.tsx   # Quick action buttons
│   │   │   │   ├── recent-signals.tsx  # Signal history display
│   │   │   │   └── stats-grid.tsx      # Performance statistics
│   │   │   ├── 📁 layout/              # Layout components
│   │   │   │   ├── sidebar.tsx         # Main navigation sidebar
│   │   │   │   └── top-header.tsx      # Top navigation header
│   │   │   ├── 📁 modals/              # Modal dialogs
│   │   │   │   └── strategy-builder-modal.tsx # Strategy configuration modal
│   │   │   └── 📁 ui/                  # Reusable UI components (shadcn/ui)
│   │   │       ├── accordion.tsx       # Collapsible content
│   │   │       ├── alert-dialog.tsx    # Confirmation dialogs
│   │   │       ├── alert.tsx           # Notification alerts
│   │   │       ├── avatar.tsx          # User avatar display
│   │   │       ├── badge.tsx           # Status badges
│   │   │       ├── button.tsx          # Button components
│   │   │       ├── card.tsx            # Content cards
│   │   │       ├── dialog.tsx          # Modal dialogs
│   │   │       ├── form.tsx            # Form components
│   │   │       ├── input.tsx           # Input fields
│   │   │       ├── sidebar.tsx         # Sidebar UI components
│   │   │       ├── table.tsx           # Data tables
│   │   │       ├── tabs.tsx            # Tab navigation
│   │   │       └── ... (30+ UI components)
│   │   ├── 📁 hooks/                   # Custom React hooks
│   │   │   ├── use-auth.tsx            # Authentication hook
│   │   │   ├── use-mobile.tsx          # Mobile detection
│   │   │   └── use-toast.ts            # Toast notifications
│   │   ├── 📁 lib/                     # Utility libraries
│   │   │   ├── protected-route.tsx     # Route protection
│   │   │   ├── queryClient.ts          # React Query setup
│   │   │   ├── utils.ts                # Utility functions
│   │   │   └── websocket.ts            # WebSocket client
│   │   ├── 📁 pages/                   # Page components
│   │   │   ├── auth-page.tsx           # Login/register page
│   │   │   ├── dashboard.tsx           # Main dashboard
│   │   │   └── not-found.tsx           # 404 page
│   │   ├── App.tsx                     # Main app component
│   │   ├── index.css                   # Global styles
│   │   └── main.tsx                    # App entry point
│   └── index.html                      # HTML template
├── 📁 server/                          # Backend Express Application
│   ├── auth.ts                         # Authentication middleware & logic
│   ├── db.ts                           # Database connection & schema
│   ├── index.ts                        # Server entry point
│   ├── routes.ts                       # API route handlers
│   ├── storage.ts                      # File storage utilities
│   └── vite.ts                         # Vite dev server integration
├── 📁 shared/                          # Shared types & schemas
│   └── schema.ts                       # TypeScript interfaces
├── 📁 attached_assets/                 # Project documentation
│   └── replit_build_plan_1750596608728.md # Build instructions
├── 📄 Configuration Files
│   ├── .replit                         # Replit configuration
│   ├── components.json                 # shadcn/ui configuration
│   ├── drizzle.config.ts              # Database ORM configuration
│   ├── package.json                   # Dependencies & scripts
│   ├── postcss.config.js              # PostCSS configuration
│   ├── tailwind.config.ts             # Tailwind CSS configuration
│   ├── tsconfig.json                  # TypeScript configuration
│   └── vite.config.ts                 # Vite build configuration
```

## 🔧 Key Features Implemented

### Frontend (Client)
- **Authentication System**: JWT-based login/logout with protected routes
- **Dashboard**: Real-time trading dashboard with live data
- **Sidebar Navigation**: Multi-tab interface (Dashboard, Signals, Strategy, Trades, Admin, Logs)
- **UI Components**: Complete shadcn/ui component library (40+ components)
- **WebSocket Integration**: Real-time data updates
- **Responsive Design**: Mobile-first design with Tailwind CSS

### Backend (Server)
- **Express API**: RESTful endpoints for all features
- **Authentication**: Passport.js with JWT sessions
- **Database**: PostgreSQL with Drizzle ORM
- **WebSocket Server**: Real-time communication
- **File Storage**: Secure file upload/download
- **API Routes**: User management, trading data, strategy configuration

### Planned Features (from build plan)
- **Desktop App**: Python modules for MT5 integration
- **Signal Parser**: Telegram signal parsing engine
- **Retry Engine**: Smart trade retry mechanism
- **Strategy Builder**: Visual strategy configuration
- **Admin Panel**: User and channel management

## 🚀 Technology Stack

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI component library
- **React Query** - Data fetching
- **React Router** - Navigation

### Backend
- **Node.js** - Runtime
- **Express.js** - Web framework
- **TypeScript** - Type safety
- **PostgreSQL** - Database
- **Drizzle ORM** - Database toolkit
- **Passport.js** - Authentication
- **WebSocket** - Real-time communication

### Development Tools
- **ESBuild** - Fast compilation
- **PostCSS** - CSS processing
- **Autoprefixer** - CSS vendor prefixes

## 📊 Current Status

### ✅ Completed
- Project structure setup
- Frontend React application with routing
- Backend Express API with authentication
- Database schema and connection
- UI component library (shadcn/ui)
- WebSocket infrastructure
- Responsive design system

### 🚧 In Progress
- Dashboard data integration
- API endpoint implementation
- Real-time data flow

### 📋 TODO (from build plan)
- MT5 Python integration modules
- Telegram signal parsing
- Strategy builder interface
- Admin panel functionality
- Trade execution engine
- Retry mechanism
- Desktop app synchronization

## 🔌 API Endpoints (Planned)

```
Authentication:
POST /auth/login
POST /auth/logout
POST /auth/refresh

User Management:
GET    /api/users
POST   /api/users
PUT    /api/users/:id
DELETE /api/users/:id

Strategy Management:
GET    /api/strategy/:userId
POST   /api/strategy/push
GET    /api/strategy/pull/:userId

Signal Management:
GET    /api/signals
POST   /api/signals
POST   /api/signal/replay

Firebridge (Desktop Sync):
POST   /api/firebridge/sync-user
POST   /api/firebridge/error-alert
GET    /api/firebridge/pull-strategy/:userId
```

## 🌐 WebSocket Events

```
Client → Server:
- status: MT5 terminal status updates
- trade: Trade execution updates

Server → Client:
- signal: New trading signals
- trade_update: Trade status changes
- error: Error notifications
```

## 🔐 Security Features

- JWT-based authentication
- Protected API routes
- Password hashing
- CORS configuration
- Input validation
- SQL injection prevention (Drizzle ORM)

## 📱 Responsive Design

- Mobile-first approach
- Collapsible sidebar
- Touch-friendly interfaces
- Adaptive layouts
- Progressive web app ready

This structure provides a solid foundation for an automated trading platform with room for expansion according to the detailed build plan.
