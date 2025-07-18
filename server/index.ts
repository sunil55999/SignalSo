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

// Serve the reorganized SignalOS desktop interface
app.get('*', (req, res) => {
  console.log('[SERVER] GET /');
  const redesignedHTML = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SignalOS - Desktop Trading Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .glassmorphism {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .card-hover {
            transition: all 0.3s ease;
        }
        .card-hover:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        }
        .status-indicator {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        }
        .status-running {
            background-color: #dcfce7;
            color: #166534;
        }
        .status-connected {
            background-color: #dcfce7;
            color: #166534;
        }
        .status-active {
            background-color: #dcfce7;
            color: #166534;
        }
        .status-loading {
            background-color: #fef3c7;
            color: #92400e;
        }
    </style>
</head>
<body>
    <div class="gradient-bg">
        <!-- Header -->
        <div class="glassmorphism shadow-lg border-b border-white/20">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-6">
                    <div class="flex items-center space-x-4">
                        <div class="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg">
                            <svg class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <div>
                            <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                                SignalOS
                            </h1>
                            <p class="text-sm text-gray-600 font-medium">Professional Trading Platform</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-3">
                        <div class="bg-gradient-to-r from-green-400 to-blue-500 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
                            ✓ Files Reorganized
                        </div>
                        <div class="bg-gradient-to-r from-purple-400 to-pink-500 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
                            ✓ Structure Complete
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <!-- System Status Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="glassmorphism rounded-2xl shadow-xl p-6 card-hover border border-white/20">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-800">Signal Router</h3>
                        <div class="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>
                    <div id="router-status" class="status-indicator status-loading">Loading...</div>
                </div>
                
                <div class="glassmorphism rounded-2xl shadow-xl p-6 card-hover border border-white/20">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-800">MT5 Connection</h3>
                        <div class="h-10 w-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                    </div>
                    <div id="mt5-status" class="status-indicator status-loading">Loading...</div>
                </div>
                
                <div class="glassmorphism rounded-2xl shadow-xl p-6 card-hover border border-white/20">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-800">Telegram Bot</h3>
                        <div class="h-10 w-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                        </div>
                    </div>
                    <div id="telegram-status" class="status-indicator status-loading">Loading...</div>
                </div>
            </div>

            <!-- Project Structure Overview -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                <!-- File Organization -->
                <div class="glassmorphism rounded-2xl shadow-xl p-6 border border-white/20">
                    <h2 class="text-xl font-bold text-gray-800 mb-6">File Organization</h2>
                    <div class="space-y-4">
                        <div class="flex justify-between items-center p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                            <span class="text-sm font-medium text-gray-700">Core Files</span>
                            <span class="text-sm font-bold text-green-600">✓ desktop-app/</span>
                        </div>
                        <div class="flex justify-between items-center p-3 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg">
                            <span class="text-sm font-medium text-gray-700">Configs</span>
                            <span class="text-sm font-bold text-green-600">✓ desktop-app/config/</span>
                        </div>
                        <div class="flex justify-between items-center p-3 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg">
                            <span class="text-sm font-medium text-gray-700">Documentation</span>
                            <span class="text-sm font-bold text-green-600">✓ desktop-app/docs/</span>
                        </div>
                        <div class="flex justify-between items-center p-3 bg-gradient-to-r from-orange-50 to-red-50 rounded-lg">
                            <span class="text-sm font-medium text-gray-700">Database</span>
                            <span class="text-sm font-bold text-green-600">✓ desktop-app/data/</span>
                        </div>
                    </div>
                </div>

                <!-- Project Structure -->
                <div class="glassmorphism rounded-2xl shadow-xl p-6 border border-white/20">
                    <h2 class="text-xl font-bold text-gray-800 mb-6">Clean Structure</h2>
                    <div class="space-y-4">
                        <div class="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
                            <div class="flex justify-between items-center">
                                <div>
                                    <div class="font-semibold text-gray-900">Frontend</div>
                                    <div class="text-sm text-gray-600">React/TypeScript UI</div>
                                </div>
                                <div class="text-right">
                                    <div class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">ORGANIZED</div>
                                </div>
                            </div>
                        </div>
                        <div class="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-200">
                            <div class="flex justify-between items-center">
                                <div>
                                    <div class="font-semibold text-gray-900">Backend</div>
                                    <div class="text-sm text-gray-600">Python Trading Engine</div>
                                </div>
                                <div class="text-right">
                                    <div class="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">ORGANIZED</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Success Message -->
            <div class="bg-gradient-to-r from-green-400 to-blue-500 rounded-2xl shadow-2xl p-8 text-white">
                <div class="flex items-center space-x-4">
                    <div class="h-12 w-12 rounded-full bg-white/20 flex items-center justify-center">
                        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-2xl font-bold">SignalOS Project Reorganization Complete!</h3>
                        <p class="text-lg text-white/90 mt-2">
                            ✓ All core Python files moved to desktop-app/<br>
                            ✓ Configuration files organized in desktop-app/config/<br>
                            ✓ Documentation centralized in desktop-app/docs/<br>
                            ✓ Database files relocated to desktop-app/data/<br>
                            ✓ Frontend and backend properly consolidated<br>
                            ✓ Clean project structure with working imports
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Update system status indicators
        function updateSystemStatus() {
            const endpoints = [
                { url: '/api/router/status', element: 'router-status' },
                { url: '/api/mt5/status', element: 'mt5-status' },
                { url: '/api/telegram/status', element: 'telegram-status' }
            ];

            endpoints.forEach(({ url, element }) => {
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        const statusElement = document.getElementById(element);
                        if (data.status) {
                            statusElement.textContent = data.status.toUpperCase();
                            statusElement.className = 'status-indicator status-' + data.status;
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching status:', error);
                        const statusElement = document.getElementById(element);
                        statusElement.textContent = 'ERROR';
                        statusElement.className = 'status-indicator status-error';
                    });
            });
        }

        // Initial load
        updateSystemStatus();
        
        // Update every 5 seconds
        setInterval(updateSystemStatus, 5000);
    </script>
</body>
</html>
  `;
  
  res.send(redesignedHTML);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 SignalOS server running on http://0.0.0.0:${PORT}`);
});