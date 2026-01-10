from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Thermostat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    location = db.Column(db.String(64), nullable=True)
    current_setpoint = db.Column(db.Float, default=20.0)
    is_on = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thermostat_id = db.Column(db.Integer, db.ForeignKey('thermostat.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    temperature = db.Column(db.Float, nullable=False)
    setpoint = db.Column(db.Float, nullable=False)
    is_on = db.Column(db.Boolean, nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thermostat_id = db.Column(db.Integer, db.ForeignKey('thermostat.id'), nullable=False)
    # Basic schedule: weekday mask + time + setpoint
    weekday_mask = db.Column(db.Integer, default=127)  # bitmask Mon-Sun
    time_h = db.Column(db.Integer, nullable=False)  # 0..23
    time_m = db.Column(db.Integer, nullable=False)  # 0..59
    setpoint = db.Column(db.Float, nullable=False)
    enabled = db.Column(db.Boolean, default=True)
