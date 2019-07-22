from colletions import namedtuple


class EditSummary(namedtuple('EditSummary',['date','message', 'wiki'])):
    __slots__ = ['date', 'message', 'wiki']

    def __init__(date, message, wiki):
        self.date = date
        self.message = message
        self.source = source

    @staticmethod
    def from_dict(d):
        return EditSummary(**d)
 
