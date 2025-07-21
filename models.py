from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Signal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    signal_type = db.Column(db.String(10), nullable=False)  # BUY/SELL
    entry_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    lot_size = db.Column(db.Float)
    status = db.Column(db.String(20), default='PENDING')  # PENDING/EXECUTED/FAILED
    confidence = db.Column(db.Float)  # AI confidence score
    raw_signal = db.Column(db.Text)  # Original signal text
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    executed_at = db.Column(db.DateTime(timezone=True))
    
    user = db.relationship('User', backref=db.backref('signals', lazy=True))
    
    def __repr__(self):
        return f'<Signal {self.symbol} {self.signal_type}>'

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signal_id = db.Column(db.Integer, db.ForeignKey('signal.id'), nullable=True)
    mt5_ticket = db.Column(db.Integer, unique=True)  # MT5 trade ticket
    symbol = db.Column(db.String(20), nullable=False)
    trade_type = db.Column(db.String(10), nullable=False)  # BUY/SELL
    volume = db.Column(db.Float, nullable=False)
    open_price = db.Column(db.Float)
    close_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    profit = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='OPEN')  # OPEN/CLOSED/PENDING
    opened_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    closed_at = db.Column(db.DateTime(timezone=True))
    
    user = db.relationship('User', backref=db.backref('trades', lazy=True))
    signal = db.relationship('Signal', backref=db.backref('trades', lazy=True))
    
    def __repr__(self):
        return f'<Trade {self.symbol} {self.trade_type} {self.volume}>'

class TradingAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    broker = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)
    equity = db.Column(db.Float, default=0.0)
    margin = db.Column(db.Float, default=0.0)
    free_margin = db.Column(db.Float, default=0.0)
    margin_level = db.Column(db.Float, default=0.0)
    server = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    user = db.relationship('User', backref=db.backref('trading_accounts', lazy=True))
    
    def __repr__(self):
        return f'<TradingAccount {self.account_number}>'