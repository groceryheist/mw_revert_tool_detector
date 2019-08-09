# rename to make it clear what's a regular expression and what's a comment
# maybe make a new class for handling regular expressions
# probably have the pattern index and the both timedPatterns be propertiers of the toolmap
# do some abstraction site metadata: maybe use mwtypes.
import datetime
import re

class TimedPattern(object):

    __slots__ = ('time', 'pattern')

    def __init__(self, time, pattern):
        self.time = time
        self.pattern = pattern

    def match(self, editSummary):
        return self.pattern.match(editSummary.message)

    def convert_to_regex(self, siteInfo):
        from .wikitextToRegex import convert
        pattern = convert(self.pattern,
                          siteInfo,
                          self.time)
        return TimedPattern(self.time, pattern)

    def as_dict(self):
        return {'time': self.time, 'pattern':self.pattern}

    @staticmethod
    def from_dict(obj):
        time = obj['time']
        pattern = obj['pattern']
        return TimedPattern(time=time, pattern=pattern)

    @staticmethod
    def from_raw_elements(time, pattern, siteInfo):
        import dateutil.parser as date_parser
        fromisoformat = date_parser.isoparse

        if not isinstance(time, datetime.datetime):
            time = fromisoformat(time)

        if not isinstance(pattern, re.Pattern):
            pattern = convert(pattern, siteInfo)

        return TimedPattern(time, pattern)
