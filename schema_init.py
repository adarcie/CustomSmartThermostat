from app import create_app
from models import db, Thermostat
app = create_app()

with app.app_context():
    db.create_all()
    # Add sample thermostats if none exist
    if Thermostat.query.count() == 0:
        t1 = Thermostat(name="Living Room", location="First floor", current_setpoint=21.0)
        t2 = Thermostat(name="Bedroom", location="Second floor", current_setpoint=19.0)
        db.session.add_all([t1, t2])
        db.session.commit()
        print("Added sample thermostats")
    else:
        print("Thermostats already exist")
