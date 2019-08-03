from patternIndex import PatternIndex, PatternIndexEncoder
from collections import defaultdict
from itertools import chain
from siteInfo import SiteInfo, SiteInfoEncoder
from json import JSONEncoder


class ToolMapEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ToolMap):
            return obj._toolMap

        if isinstance(obj, PatternIndex):
            return PatternIndexEncoder.default(obj)

        if isinstance(obj, SiteInfo):
            return SiteInfoEncoder.default(obj)

        else:
            return JSONEncoder.default(obj)


class ToolMap(object):

    __slots__ = ('_toolMap')

    def __init__(self):
        self._toolMap = defaultdict(PatternIndex)

    def empty(self):
        return len(self._toolMap) == 0

    @staticmethod
    def from_dict(toolMap):
        obj = ToolMap()
        if not isinstance(toolMap, defaultdict(PatternIndex)):
            obj._toolMap.update(toolMap)

        else:
            obj._toolMap = toolMap

        return obj

    # we need to make sure that the patterns are sorted before we convert them
    def add(self, prop, time=None, pattern=None, timedPattern=None):
        self._toolMap[prop].add(
            time=time, pattern=pattern, timedPattern=timedPattern)

    def convert_to_regex(self, siteInfo):
        self._toolMap = {
            prop: index.convert_to_regex(siteInfo)
            for prop, index in self._toolMap.items()
        }
        return self

    @staticmethod
    def from_json_dict(jsonobj):
        return ToolMap.from_dict({prop: PatternIndex.from_json_dict(values) for prop, values in jsonobj.items()})

    def merge(self, other):
        merged = {k: self._toolMap[k].merge(other._toolMap[k])
                  for k in set(chain(self._toolMap.keys(),
                                     other._toolMap.keys())
                               )
                  }
        self._toolMap = defaultdict(PatternIndex)
        self._toolMap.update(merged)
        return self

    def match(self, editSummary):
        for prop, index in self._toolMap.items():
            if index.match(editSummary):
                yield prop

    def __repr__(self):
        return self._toolMap.__repr__()
