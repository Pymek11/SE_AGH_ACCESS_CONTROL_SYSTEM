from app.api.routes import router
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.database import engine, Base
from app.api.admin import router as admin_router


# Import models so they are registered on the metadata
import app.models.qr_image  # noqa: F401
from app.models.qr_image import metadata as core_metadata


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
	"""Create database tables and exit."""
	# NOTE: this project primarily uses SQLAlchemy Core tables defined under
	# app.models.qr_image.metadata (employees, etc.). We create both.
	Base.metadata.create_all(bind=engine)
	core_metadata.create_all(bind=engine)
	print("Database tables created (if not existing) in `access_control.db`")
	yield

app = FastAPI(title="SE AGH Access Control System", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
app.include_router(admin_router)
if __name__ == "__main__":
	import uvicorn
	uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
