from app import app, db
from models import User

with app.app_context():
    existing_user = User.query.filter_by(id=1).first()
    
    if not existing_user:
        default_user = User(
            id=1,
            username='demo_user',
            email='demo@movierecommender.com'
        )
        db.session.add(default_user)
        db.session.commit()
        print("Default user created successfully!")
    else:
        print("Default user already exists.")
