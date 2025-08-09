import logging
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.engine.url import make_url, URL # Import URL type as well

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

try:
    from app.db.base_class import Base
    from app.db.session import engine 
    from app.db.models import Lecture, Slide, TranscriptionSegment  # noqa: F401 
    from app.core.config import settings
except ImportError as e:
    logging.error(f"Failed to import application modules. Ensure you are running this script from the 'notelecture-backend' directory or that '{project_root}' is in your PYTHONPATH.")
    logging.error(f"ImportError: {e}")
    sys.exit(1) # Exit if imports fail

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)-8s - %(message)s")
logger = logging.getLogger(__name__)

def create_database_if_not_exists(database_url: str):
    """
    Connects to the MySQL server (without a specific database) and
    creates the target database if it doesn't exist.
    """
    # Parse the database URL string using make_url for SQLAlchemy 2.x
    try:
        url = make_url(database_url)
    except Exception as e:
        logger.error(f"Invalid DATABASE_URL format: {database_url}")
        logger.error(f"Parsing error: {e}")
        sys.exit(1)

    db_name = url.database

    if not db_name:
        logger.error("DATABASE_URL does not specify a database name. Cannot create database.")
        sys.exit(1)

    url_dict = url.translate_connect_args() # Gets connection arguments as a dict
    url_dict.pop('database', None) # Remove the database key if it exists


    server_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=None # Explicitly set database to None
        # Add other parts like query if needed, but usually not for this simple case
    )

    # For security, mask password in logs
    server_url_masked = server_url.render_as_string(hide_password=True)
    logger.info(f"Attempting to connect to MySQL server using {server_url_masked} to create database '{db_name}'...")

    temp_engine = None
    try:
        temp_engine = create_engine(server_url, pool_size=2, max_overflow=0)

        # Connect and execute the CREATE DATABASE command
        with temp_engine.connect() as connection:
            logger.info(f"Executing CREATE DATABASE IF NOT EXISTS `{db_name}` ...")
            try:
                # CORRECTED COLLATE NAME: utf8mb4_unicode_ci
                connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
                # Explicitly commit in case autocommit is off for the driver
                connection.execute(text("COMMIT;"))
                logger.info(f"Database '{db_name}' checked/created successfully.")
            except Exception as exec_err:
                 logger.error(f"Error during CREATE DATABASE execution: {exec_err}")
                 # Try a rollback just in case, although DDL often implies commit
                 try: connection.rollback()
                 except Exception: pass # Ignore rollback error if connection is truly bad
                 raise exec_err # Re-raise the execution error


    except (OperationalError, ProgrammingError) as e:
         logger.error(f"Error connecting to MySQL server or executing CREATE DATABASE.")
         logger.error(f"Error details: {e}")
         # Check if the error is "Access denied" or related permissions issues
         if "Access denied" in str(e) or "privilege" in str(e) or "authentication" in str(e).lower():
             logger.error("This might be a permissions or authentication issue. The user specified in DATABASE_URL needs permissions to connect to the server (without a default database) AND CREATE DATABASE privilege.")
         sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while attempting to create the database: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Dispose the temporary engine connections
        if temp_engine:
             temp_engine.dispose()
             logger.info("Temporary engine for database creation disposed.")

def create_tables():
    """
    Ensures the database exists and then creates all tables
    defined in models using SQLAlchemy.
    """
    # Ensure the database exists first
    create_database_if_not_exists(settings.DATABASE_URL)


    logger.info(f"Attempting to create tables in database '{engine.url.database}' using the main engine...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables creation process completed.")
        logger.info("If no errors were reported above after 'Database tables creation process completed.', tables were likely created successfully.")

    except Exception as e:
        logger.error(f"An error occurred while creating tables: {e}", exc_info=True)
        sys.exit(1) # Exit with error code

if __name__ == "__main__":
    create_tables()