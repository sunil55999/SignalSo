const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 5000;

// Simple MIME type detection
const getMimeType = (filePath) => {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.tsx': 'text/javascript',
    '.ts': 'text/javascript'
  };
  return mimeTypes[ext] || 'application/octet-stream';
};

// Simple API responses
const handleAPI = (req, res, pathname) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  let body = '';
  req.on('data', chunk => {
    body += chunk.toString();
  });

  req.on('end', () => {
    try {
      const parsedBody = body ? JSON.parse(body) : {};
      
      switch (pathname) {
        case '/api/health':
          res.writeHead(200);
          res.end(JSON.stringify({ 
            status: 'healthy', 
            timestamp: new Date().toISOString(),
            version: '1.0.0'
          }));
          break;
          
        case '/api/auth/login':
          if (req.method === 'POST') {
            const { username, password } = parsedBody;
            if (username === 'demo' && password === 'demo123') {
              res.writeHead(200);
              res.end(JSON.stringify({ 
                success: true, 
                user: { id: '1', username: 'demo', email: 'demo@example.com' },
                token: 'mock-jwt-token'
              }));
            } else {
              res.writeHead(401);
              res.end(JSON.stringify({ success: false, error: 'Invalid credentials' }));
            }
          }
          break;
          
        case '/api/router/start':
          res.writeHead(200);
          res.end(JSON.stringify({ success: true }));
          break;
          
        case '/api/router/status':
          res.writeHead(200);
          res.end(JSON.stringify({
            status: 'running',
            uptime: 3600,
            activeTasks: 5,
            lastStarted: new Date().toISOString()
          }));
          break;
          
        case '/api/mt5/status':
          res.writeHead(200);
          res.end(JSON.stringify({
            status: 'connected',
            account: 'Demo Account',
            balance: 10000,
            equity: 10000,
            lastConnected: new Date().toISOString()
          }));
          break;
          
        case '/api/telegram/status':
          res.writeHead(200);
          res.end(JSON.stringify({
            status: 'connected',
            username: 'demo_user',
            channelCount: 3,
            lastMessage: 'BUY EURUSD @ 1.0850',
            lastMessageTime: new Date().toISOString()
          }));
          break;
          
        case '/api/logs':
          const mockLogs = [
            { id: '1', level: 'info', message: 'Router started successfully', timestamp: new Date().toISOString(), component: 'router' },
            { id: '2', level: 'info', message: 'MT5 connection established', timestamp: new Date().toISOString(), component: 'mt5' },
            { id: '3', level: 'info', message: 'Telegram authentication completed', timestamp: new Date().toISOString(), component: 'telegram' }
          ];
          res.writeHead(200);
          res.end(JSON.stringify(mockLogs));
          break;
          
        case '/api/logs/stats':
          res.writeHead(200);
          res.end(JSON.stringify({
            total: 100,
            byLevel: { info: 80, warning: 15, error: 5 },
            byComponent: { router: 30, mt5: 25, telegram: 25, system: 20 }
          }));
          break;
          
        default:
          res.writeHead(404);
          res.end(JSON.stringify({ error: 'API endpoint not found' }));
      }
    } catch (error) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: 'Internal server error' }));
    }
  });
};

// Simple static file serving
const serveFile = (req, res, filePath) => {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('File not found');
      return;
    }
    
    res.setHeader('Content-Type', getMimeType(filePath));
    res.writeHead(200);
    res.end(data);
  });
};

// Main server
const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  
  console.log(`[SERVER] ${req.method} ${pathname}`);
  
  // Handle API routes
  if (pathname.startsWith('/api/')) {
    handleAPI(req, res, pathname);
    return;
  }
  
  // Handle static files
  const clientDir = path.join(__dirname, '../client');
  let filePath;
  
  if (pathname === '/') {
    filePath = path.join(clientDir, 'index.html');
  } else {
    filePath = path.join(clientDir, pathname);
  }
  
  // Check if file exists
  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // If file doesn't exist, serve index.html for SPA routing
      serveFile(req, res, path.join(clientDir, 'index.html'));
    } else {
      serveFile(req, res, filePath);
    }
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 SignalOS server running on http://0.0.0.0:${PORT}`);
});

module.exports = server;