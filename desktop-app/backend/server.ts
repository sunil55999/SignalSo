import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Serve static files from the frontend build
app.use(express.static(path.join(__dirname, '../build')));

// API routes
app.get('/api/router/status', (req, res) => {
  res.json({ status: 'running', timestamp: new Date().toISOString() });
});

app.get('/api/mt5/status', (req, res) => {
  res.json({ status: 'connected', timestamp: new Date().toISOString() });
});

app.get('/api/telegram/status', (req, res) => {
  res.json({ status: 'active', timestamp: new Date().toISOString() });
});

// Handle React Router
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../build/index.html'));
});

app.listen(port, () => {
  console.log(`🚀 SignalOS Desktop App running on http://0.0.0.0:${port}`);
});