from sortedcontainers import SortedList
from collections import namedtuple
from .util import fromisoformat, get_previous_time_from_index
import re
from json import JSONEncoder
from datetime import datetime
from .timedPattern import TimedPattern
from functools import partial

def _dottime(timedPattern):
    return timedPattern.time

TimedPatternSortedList = partial(SortedList, key = _dottime)

class PatternIndexEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TimedPatternSortedList):
            return list(obj)

        if isinstance(obj, TimedPattern):
            return {'time':obj.time, "pattern":obj.pattern}

        if isinstance(obj, datetime):
            return obj.iso_format()

        if isinstance(obj, re.Pattern):
            return obj.pattern
        
        return JSONEncoder.default(obj)

class PatternIndex(object):
    __slots__ = ['index', 'ready']

    def __init__(self):
        self.index = TimedPatternSortedList()
        self.ready = False
        
    @staticmethod
    def from_time_pattern(time, pattern):
        tp = TimePattern.from_elements(time, pattern)
        obj = PatternIndex()
        obj.add(time=time, pattern=pattern)
        return obj

    @staticmethod
    def from_timed_patterns(timedPatterns, ready=False):
        obj = PatternIndex()

        if isinstance(timedPatterns, TimedPattern):
            obj.index = TimedPatternSortedList([timedPatterns])
        else:
            obj.index = TimedPatternSortedList(timedPatterns)

        obj.ready = ready
        return obj
        

    def to_save(self):
        return [item.as_dict() for item in self.index]

    @staticmethod
    def from_save(saveobj):
        obj = PatternIndex.from_timed_patterns([TimedPattern.from_dict(e) for e in saveobj])
        obj.ready = True
        return obj

    @staticmethod
    def from_json_dict(jsondict):
        patterns = map(TimedPattern.from_json_dict, jsondict)
        patternIndex = PatternIndex.from_timed_patterns(patterns)
        return patternIndex

    def add(self, time=None, pattern=None, timedPattern=None):
        if time is not None and pattern is not None:
            timedPattern = TimedPattern(time, pattern)
        elif timedPattern is not None:
            timedPattern = timedPattern
        else:
            raise ValueError("""
            either time and pattern or timedPattern must not be None
            """)

        previous_pattern = get_previous_time_from_index(self.index, timedPattern.time)
        if previous_pattern != timedPattern.pattern:
            self.index.add(timedPattern)

    def convert_to_regex(self, siteInfo):

        patterns = map(lambda tp: tp.convert_to_regex(siteInfo), self.index)
        patterns = list(patterns)
        self.index = TimedPatternSortedList(patterns)
        self.ready = True
        
        return self

    # def add(self, timedPattern, siteInfo):
    #     previous_time = self.index.bisect_right(timedPattern) - 1
    #     if self.index[previous_time].pattern != timedPattern.pattern:
    #         self.index.add(TimedPattern.from_raw_elements(time=time, pattern=pattern, siteInfo=siteInfo))

    #     else:
    #         d[wiki] = ToolMap(wiki=wiki)
    #         d[wiki].add(prop=prop,pattern=pattern,time=time)
    #         [prop] = SortedPairList([(time, pattern)])

    def is_empty(self):
        return self.index is None or len(self.index) == 0
    
    def merge(self, other):
        if other is None or other.is_empty():
            return self

        if self.is_empty():
            self.index = other.index

        min_other = other.index[0]
        kept_other = other.index.irange(None, min_other, inclusive=(True, False))
        self.index.update(kept_other)

        return self

    def match(self, editSummary):
        if not self.ready:
            self.convert_to_regex()

        previous_time = get_previous_time_from_index(self.index, editSummary.datetime)
        pattern = self.index[previous_time]
        return pattern.match(editSummary)

    
    def __repr__(self):
        return {'index':self.index, 'ready':self.ready}.__repr__()
