from alembic import context
from sqlalchemy import create_engine
from ada.config import settings
from ada.db.models import Base

def run():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
run()
