from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class Booking:
    """Модель записи на консультацию"""
    user_id: int
    username: str
    date: str
    time: str
    contact_info: str
    event_id: Optional[str] = None
    status: str = "confirmed"  # confirmed, cancelled
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    id: Optional[int] = None

    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'date': self.date,
            'time': self.time,
            'contact_info': self.contact_info,
            'event_id': self.event_id,
            'status': self.status,
            'created_at': self.created_at
        }

@dataclass
class TimeSlot:
    """Модель временного слота"""
    date: str
    time: str
    datetime: datetime
    is_available: bool = True