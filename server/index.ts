import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import routes from './routes';
import { logManager } from '../src/logs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
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
  logManager.info(`${req.method} ${req.path}`, 'server');
  next();
});

// API routes
app.use('/api', routes);

// Serve static files in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../dist/client')));
  
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../dist/client/index.html'));
  });
} else {
  // In development mode, serve a basic development message
  app.get('/', (req, res) => {
    res.send(`
      <html>
        <head>
          <title>SignalOS - Development Mode</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 20px; background: #f0f8ff; border-radius: 8px; margin: 20px 0; }
            .endpoint { padding: 10px; background: #f5f5f5; border-radius: 4px; margin: 10px 0; }
            .healthy { color: #00aa00; }
            .error { color: #aa0000; }
          </style>
        </head>
        <body>
          <div class="container">
            <h1>🚀 SignalOS - Trading Automation Platform</h1>
            <div class="status">
              <h3>Server Status: <span class="healthy">Running</span></h3>
              <p>The SignalOS backend server is running successfully on port 3000.</p>
            </div>
            
            <h3>API Endpoints</h3>
            <div class="endpoint">
              <strong>GET /api/health</strong> - Health check endpoint
            </div>
            <div class="endpoint">
              <strong>POST /api/auth/login</strong> - User authentication
            </div>
            <div class="endpoint">
              <strong>GET /api/mt5/status</strong> - MT5 connection status
            </div>
            <div class="endpoint">
              <strong>GET /api/telegram/status</strong> - Telegram session status
            </div>
            <div class="endpoint">
              <strong>GET /api/logs</strong> - System logs
            </div>
            <div class="endpoint">
              <strong>POST /api/router/start</strong> - Start signal router
            </div>
            
            <h3>Development Information</h3>
            <p>The SignalOS server is running in development mode. The frontend build needs to be configured to serve the full web interface.</p>
            
            <h3>Next Steps</h3>
            <ul>
              <li>Use the API endpoints above to interact with the system</li>
              <li>Configure the frontend build for the web interface</li>
              <li>Set up MT5 connection via API</li>
              <li>Configure Telegram integration</li>
            </ul>
          </div>
        </body>
      </html>
    `);
  });
}

// Error handling middleware
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  logManager.error(`Server error: ${err.message}`, 'server', { 
    path: req.path,
    method: req.method,
    stack: err.stack
  });
  
  res.status(500).json({
    success: false,
    error: process.env.NODE_ENV === 'production' ? 'Internal server error' : err.message
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  logManager.info(`SignalOS server running on port ${PORT}`, 'server');
  console.log(`🚀 SignalOS server running on http://0.0.0.0:${PORT}`);
});

export default app;