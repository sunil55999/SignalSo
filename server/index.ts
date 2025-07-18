import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// API Routes
app.get('/api/router/status', (req, res) => {
  console.log('[SERVER] GET /api/router/status');
  res.json({ status: 'running' });
});

app.get('/api/mt5/status', (req, res) => {
  console.log('[SERVER] GET /api/mt5/status');
  res.json({ status: 'connected' });
});

app.get('/api/telegram/status', (req, res) => {
  console.log('[SERVER] GET /api/telegram/status');
  res.json({ status: 'active' });
});

app.get('/api/status', (req, res) => {
  res.json({
    status: 'online',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Serve the React-based SignalOS dashboard
app.use(express.static(path.join(__dirname, '..', 'dist')));

// Serve the main React app for all routes
app.get('*', (req, res) => {
  console.log('[SERVER] GET /');
  res.sendFile(path.join(__dirname, '..', 'dist', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 SignalOS server running on http://0.0.0.0:${PORT}`);
});