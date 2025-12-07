from app.core.database import engine
from app.models.qr_image import metadata


def main():
    metadata.create_all(engine)
    print("Created tables:", list(metadata.tables.keys()))


if __name__ == '__main__':
    main()
