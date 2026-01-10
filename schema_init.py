from app import create_app
from models import db, Thermostat
app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    # Add sample thermostats if none exist
    if Thermostat.query.count() == 0:
        t1 = Thermostat(
            name="Living Room",
            location="First floor",
            current_setpoint=21.0,
            hysteresis_up=0.5,
            hysteresis_down=0.5,
            min_temp=5.0,
            max_temp=30.0,
            eco_setpoint=16.0
        )
        t2 = Thermostat(
            name="Bedroom",
            location="Second floor",
            current_setpoint=19.0,
            hysteresis_up=0.5,
            hysteresis_down=0.5,
            min_temp=5.0,
            max_temp=30.0,
            eco_setpoint=16.0
        )
        db.session.add_all([t1, t2])
        db.session.commit()
        print("Added sample thermostats (DB recreated)")
    else:
        print("Thermostats already exist")
