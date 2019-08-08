from .util import fromisoformat
from datetime import timezone 

class EditSummary(object):
    __slots__ = ['datetime', 'message', 'wiki']

    def __init__(self, date, message, wiki):
        if isinstance(date, str):
            date = fromisoformat(date)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)

        self.datetime = date
        self.message = message
        self.wiki = wiki

    @staticmethod
    def from_dict(d):
        return EditSummary(**d)
