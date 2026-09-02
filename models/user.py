from models import db


class Users(db.Model):
    __tablename__ = "users"

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Auth
    email = db.Column(db.String(150), nullable=False, unique=True)
    username = db.Column(db.String(25), nullable=False)
    phone_number = db.Column(db.String(20))
    password = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now()
    )

    bio = db.Column(db.String(1000), nullable=True)
    location = db.Column(db.String(100))

    # Account Status
    is_active = db.Column(
        db.Boolean,
        default=True
    )


    def __repr__(self):
        return f"<User {self.email}>"
