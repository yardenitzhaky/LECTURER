"""Database utility functions."""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def update_lecture_status(db: Session, lecture_id: int, status: str) -> bool:
    """
    Helper function to update lecture status with proper error handling and locking.
    
    Args:
        db: Database session
        lecture_id: ID of the lecture to update
        status: New status to set
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        from app.db.models import Lecture
        
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).with_for_update().first()
        if lecture:
            lecture.status = status
            db.commit()
            logger.info(f"Lecture ID {lecture_id} status updated to: {status}")
            return True
        else:
            logger.warning(f"Attempted status update for non-existent lecture ID: {lecture_id}")
            return False
    except Exception as e:
        logger.error(f"Failed to update status for lecture {lecture_id} to {status}: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception as rb_exc:
            logger.error(f"Rollback failed during status update failure for lecture {lecture_id}: {rb_exc}", exc_info=True)
        return False


def check_column_exists(db: Session, table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a table.
    
    Args:
        db: Database session
        table_name: Name of the table
        column_name: Name of the column to check
        
    Returns:
        True if column exists, False otherwise
    """
    try:
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = :table_name 
            AND COLUMN_NAME = :column_name
        """), {"table_name": table_name, "column_name": column_name})
        
        return result.scalar() > 0
    except Exception as e:
        logger.error(f"Error checking if column {column_name} exists in table {table_name}: {e}")
        return False