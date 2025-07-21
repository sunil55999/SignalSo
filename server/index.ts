#!/usr/bin/env node
/**
 * SignalOS Backend Proxy
 * 
 * This server acts as a proxy to the Python FastAPI backend.
 * The UI has been removed and only the backend API services remain.
 */

import { spawn } from 'child_process';
import path from 'path';

const BACKEND_DIR = path.resolve(__dirname, '../backend');
const PORT = process.env.PORT || 5000;

console.log('🚀 SignalOS Backend Proxy starting...');
console.log(`📁 Backend directory: ${BACKEND_DIR}`);

// Start the Python FastAPI backend
const pythonProcess = spawn('python3', ['main.py'], {
  cwd: BACKEND_DIR,
  stdio: 'inherit',
  env: {
    ...process.env,
    PORT: PORT.toString(),
  }
});

pythonProcess.on('error', (error) => {
  console.error('❌ Failed to start Python backend:', error);
  process.exit(1);
});

pythonProcess.on('exit', (code) => {
  console.log(`🔄 Python backend process exited with code ${code}`);
  if (code !== 0) {
    console.error('❌ Backend process failed');
    process.exit(code || 1);
  }
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down SignalOS Backend...');
  pythonProcess.kill('SIGINT');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Terminating SignalOS Backend...');
  pythonProcess.kill('SIGTERM');
  process.exit(0);
});

// Keep the process running
console.log(`🚀 SignalOS Backend Proxy is running on port ${PORT}`);
console.log('✅ UI components have been removed - Backend API services only');