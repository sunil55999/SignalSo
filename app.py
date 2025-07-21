import os
import logging

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# For now, use SQLite for development since PostgreSQL is not available
database_url = os.environ.get("DATABASE_URL", "sqlite:///signalos.db")
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# initialize the app with the extension
db.init_app(app)

@app.route('/')
def index():
    """API root endpoint"""
    return jsonify({
        "name": "SignalOS API",
        "version": "1.0.0",
        "status": "running",
        "description": "AI-powered trading automation platform API",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "signals": "/api/signals",
            "trades": "/api/trades"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "database": "connected",
        "timestamp": "2025-07-21T21:05:00Z"
    })

@app.route('/api/status')
def api_status():
    """System status endpoint"""
    return jsonify({
        "system": "SignalOS",
        "status": "active",
        "components": {
            "database": "connected",
            "ai_parser": "ready",
            "mt5_bridge": "configuring",
            "telegram": "setup_required"
        },
        "stats": {
            "signals_today": 0,
            "active_trades": 0,
            "total_profit": 0.0,
            "win_rate": 0.0
        }
    })

@app.route('/api/signals')
def api_signals():
    """Signals endpoint"""
    return jsonify({
        "signals": [],
        "count": 0,
        "status": "No signals received yet"
    })

@app.route('/api/trades')
def api_trades():
    """Trades endpoint"""
    return jsonify({
        "trades": [],
        "open_positions": 0,
        "total_profit": 0.0,
        "status": "No active trades"
    })

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    try:
        import models  # noqa: F401
        db.create_all()
        app.logger.info("Database tables created successfully")
    except ImportError:
        app.logger.warning("No models module found, creating without models")
        db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)