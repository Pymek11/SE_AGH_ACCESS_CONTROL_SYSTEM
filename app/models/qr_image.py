from sqlalchemy import Table, MetaData, Column, Integer, String, LargeBinary, DateTime
from sqlalchemy import func

# Define the employees table using SQLAlchemy Core (no ORM class)
metadata = MetaData()

employees = Table(
    "employees",
    metadata,
    Column("emp_id", Integer, primary_key=True, autoincrement=True),
    Column("emp_name", String(100), nullable=True),
    Column("emp_qr_code", LargeBinary, nullable=True),
    Column("emp_photo", LargeBinary, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

# Store unauthorized access attempts for audit/debug.
# - qr_text: the decoded QR payload used
# - photo: a JPEG snapshot from the camera at the time the attempts were exhausted
# - created_at: server timestamp
unauthorized_access = Table(
    "unauthorized_access",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("qr_text", String(512), nullable=True),
    Column("photo", LargeBinary, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

def create_tables(engine):
    """Create the employees table in the target database."""
    metadata.create_all(engine)


__all__ = ["employees", "unauthorized_access", "metadata", "create_tables"]
