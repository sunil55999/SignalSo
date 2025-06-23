module.exports = {
  apps: [
    {
      name: 'signalos-server',
      script: '../server/index.js',
      instances: 1,
      exec_mode: 'cluster',
      env: {
        NODE_ENV: 'production',
        PORT: 5000
      },
      env_production: {
        NODE_ENV: 'production',
        PORT: 5000
      },
      error_file: '../logs/server-error.log',
      out_file: '../logs/server-out.log',
      log_file: '../logs/server-combined.log',
      time: true,
      max_memory_restart: '500M',
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '10s',
      watch: false,
      ignore_watch: ['node_modules', 'logs', '*.log']
    },
    {
      name: 'signalos-desktop-sync',
      script: '../desktop-app/auto_sync.py',
      interpreter: 'python3',
      instances: 1,
      exec_mode: 'fork',
      env: {
        PYTHONPATH: '../desktop-app',
        CONFIG_FILE: '../desktop-app/config.json'
      },
      error_file: '../logs/sync-error.log',
      out_file: '../logs/sync-out.log',
      log_file: '../logs/sync-combined.log',
      time: true,
      restart_delay: 10000,
      max_restarts: 5,
      min_uptime: '30s',
      watch: false
    },
    {
      name: 'signalos-telegram-bot',
      script: '../desktop-app/copilot_bot.py',
      interpreter: 'python3',
      instances: 1,
      exec_mode: 'fork',
      env: {
        PYTHONPATH: '../desktop-app',
        CONFIG_FILE: '../desktop-app/config.json'
      },
      error_file: '../logs/bot-error.log',
      out_file: '../logs/bot-out.log',
      log_file: '../logs/bot-combined.log',
      time: true,
      restart_delay: 15000,
      max_restarts: 5,
      min_uptime: '30s',
      watch: false,
      autorestart: true
    }
  ],
  
  deploy: {
    production: {
      user: 'deploy',
      host: 'your-server.com',
      ref: 'origin/main',
      repo: 'git@github.com:your-username/signalos.git',
      path: '/var/www/signalos',
      'pre-deploy-local': '',
      'post-deploy': 'npm install && npm run build && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};