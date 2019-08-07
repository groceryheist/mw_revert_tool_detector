# rename to make it clear what's a regular expression and what's a comment
# maybe make a new class for handling regular expressions
# probably have the pattern index and the both timedPatterns be propertiers of the toolmap
# do some abstraction site metadata: maybe use mwtypes.
from collections import namedtuple
import datetime
import re
import dateutil.parser as date_parser
fromisoformat = date_parser.isoparse
from .wikitextToRegex import convert

class TimedPattern(namedtuple('TimedPattern', ['time', 'pattern'])):

    @staticmethod
    def from_raw_elements(time, pattern, siteInfo):
        if not isinstance(time, datetime.datetime):
            time = fromisoformat(time)

        if not isinstance(pattern, re.Pattern):
            pattern = convert(pattern, siteInfo)

        return TimedPattern(time, pattern)

    def convert_to_regex(self, siteInfo):
        pattern = convert(self.pattern,
                          siteInfo,
                          self.time)
        return TimedPattern(self.time, pattern)

    @staticmethod
    def from_json_dict(jsonobj):
        time = date_parser.parse(jsonobj['time'])
        pattern = jsonobj.compile(jsonobj['pattern'])
        return TimedPattern(time=time, pattern=pattern)

    def match(self, editSummary):
        return self.pattern.match(editSummary.message)
