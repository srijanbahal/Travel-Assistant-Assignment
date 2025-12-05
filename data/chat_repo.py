from sqlalchemy.orm import Session
from data.database import ChatHistory, get_db
import datetime

def save_chat_message(session_id: str, sender: str, message: str):
    db = next(get_db())
    try:
        chat_entry = ChatHistory(
            session_id=session_id,
            sender=sender,
            message=message,
            timestamp=datetime.datetime.now().isoformat()
        )
        db.add(chat_entry)
        db.commit()
    except Exception as e:
        print(f"Error saving chat: {e}")
    finally:
        db.close()

def get_chat_history(session_id: str):
    db = next(get_db())
    try:
        return db.query(ChatHistory).filter(ChatHistory.session_id == session_id).order_by(ChatHistory.id).all()
    finally:
        db.close()
