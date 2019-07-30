from util import fromisoformat

class EditSummary(object):
    __slots__ = ['datetime', 'message', 'wiki']

    def __init__(datetime, message, wiki):
        if isinstance(datetime, str):
            date = fromisoformat(str)
        self.datetime = datetime
        self.message = message
        self.wiki = wiki

    @staticmethod
    def from_dict(d):
        return EditSummary(**d)
 
