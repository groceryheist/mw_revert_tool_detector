from patternIndex import PatternIndex, PatternIndexEncoder
from collections import defaultdict
from itertools import chain

from editSummary import EditSummary

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

    def from_dict(toolMap):
        self._toolMap = toolMap

    # we need to make sure that the patterns are sorted before we convert them
    def add(self, prop, time = None, pattern = None, timedPattern = None):
            self._toolMap[prop].add(time=time, pattern=pattern, timedPattern=timedPattern)


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

        self._toolMap = {k : self._toolMap[k].merge(other._toolMap[k])
                         for k in set(chain(self._toolMap.keys(),
                                            other._toolMap.keys())
                                      )
                         }
        return self

        
    def match(self, editSummary):
        def _match(toolMap, editSummary):
            for prop, index in toolMap.keys():
                if index.match(editSummary):
                    return prop
        return None

    def __repr__(self):
        return self._toolMap.__repr__()
