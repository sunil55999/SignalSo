const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 5000;

// Basic middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// CORS middleware
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});

// Request logging
app.use((req, res, next) => {
  console.log(`[SERVER] ${req.method} ${req.path}`);
  next();
});

// API routes - simplified and working
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

app.post('/api/auth/login', (req, res) => {
  const { username, password } = req.body;
  // Simple mock authentication
  if (username === 'demo' && password === 'demo123') {
    res.json({ 
      success: true, 
      user: { id: '1', username: 'demo', email: 'demo@example.com' },
      token: 'mock-jwt-token'
    });
  } else {
    res.status(401).json({ success: false, error: 'Invalid credentials' });
  }
});

app.post('/api/router/start', (req, res) => {
  res.json({ success: true });
});

app.post('/api/router/stop', (req, res) => {
  res.json({ success: true });
});

app.get('/api/router/status', (req, res) => {
  res.json({
    status: 'running',
    uptime: 3600,
    activeTasks: 5,
    lastStarted: new Date().toISOString()
  });
});

app.get('/api/mt5/status', (req, res) => {
  res.json({
    status: 'connected',
    account: 'Demo Account',
    balance: 10000,
    equity: 10000,
    lastConnected: new Date().toISOString()
  });
});

app.post('/api/mt5/connect', (req, res) => {
  res.json({ success: true });
});

app.post('/api/mt5/disconnect', (req, res) => {
  res.json({ success: true });
});

app.get('/api/telegram/status', (req, res) => {
  res.json({
    status: 'connected',
    username: 'demo_user',
    channelCount: 3,
    lastMessage: 'BUY EURUSD @ 1.0850',
    lastMessageTime: new Date().toISOString()
  });
});

app.post('/api/telegram/login', (req, res) => {
  res.json({ success: true });
});

app.post('/api/telegram/logout', (req, res) => {
  res.json({ success: true });
});

app.get('/api/logs', (req, res) => {
  const mockLogs = [
    { id: '1', level: 'info', message: 'Router started successfully', timestamp: new Date().toISOString(), component: 'router' },
    { id: '2', level: 'info', message: 'MT5 connection established', timestamp: new Date().toISOString(), component: 'mt5' },
    { id: '3', level: 'info', message: 'Telegram authentication completed', timestamp: new Date().toISOString(), component: 'telegram' },
    { id: '4', level: 'info', message: 'System health check passed', timestamp: new Date().toISOString(), component: 'system' },
    { id: '5', level: 'warning', message: 'High CPU usage detected', timestamp: new Date().toISOString(), component: 'system' }
  ];
  res.json(mockLogs);
});

app.get('/api/logs/stats', (req, res) => {
  res.json({
    total: 100,
    byLevel: { info: 80, warning: 15, error: 5 },
    byComponent: { router: 30, mt5: 25, telegram: 25, system: 20 }
  });
});

app.get('/api/bridge/status', (req, res) => {
  res.json({
    status: 'active',
    version: '1.0.0',
    lastUpdate: new Date().toISOString()
  });
});

app.post('/api/bridge/connect', (req, res) => {
  res.json({ success: true });
});

// Serve static files from client directory
app.use(express.static(path.join(__dirname, '../client')));

// Handle React Router - serve index.html for all non-API routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../client/index.html'));
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 SignalOS server running on http://0.0.0.0:${PORT}`);
});

module.exports = app;