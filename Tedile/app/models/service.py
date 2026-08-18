from app.extensions import db


class Service(db.Model):
    """A bookable service category, e.g. Plumber, Electrician."""

    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    display_group = db.Column(db.String(120))
    icon_key = db.Column(db.String(120))

    def to_public_dto(self):
        return {
            "name": self.name,
            "slug": self.slug,
            "display_order": self.display_order,
            "display_group": self.display_group,
            "icon_key": self.icon_key,
        }

    def to_public_dict(self):
        return self.to_public_dto()

    def to_admin_dto(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "is_active": self.is_active,
            "display_order": self.display_order,
            "display_group": self.display_group,
            "icon_key": self.icon_key,
        }
