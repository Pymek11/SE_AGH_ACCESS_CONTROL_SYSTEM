"""Entry point for the application (minimal DB table creation).

Run instructions are described in the repository README.
"""
from app.core.database import engine, Base

# Import models so they are registered on the metadata
import app.models.qr_image  # noqa: F401


def main() -> None:
	"""Create database tables and exit."""
	Base.metadata.create_all(bind=engine)
	print("Database tables created (if not existing) in `access_control.db`")


if __name__ == "__main__":
	main()
