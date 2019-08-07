from .util import fromisoformat


class EditSummary(object):
    __slots__ = ['datetime', 'message', 'wiki']

    def __init__(self, date, message, wiki):
        if isinstance(date, str):
            date = fromisoformat(date)
        self.datetime = date
        self.message = message
        self.wiki = wiki

    @staticmethod
    def from_dict(d):
        return EditSummary(**d)
