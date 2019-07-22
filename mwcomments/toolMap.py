from .patternIndex import PatternIndex, PatternIndexEncoder
from collections import defaultdict
from itertools import chain

from .editSummary import EditSummary

from json import JSONEncoder

class ToolMapEncoder(PatternIndexEncoder):
    def to_json_dict(self):

    def default(self, obj):
        if isinstance(ToolMap):
            d = {'toolMap':self._toolMap}
            d['fallbacks'] = self.fallbacks
            return d

        return PatternIndexEncoder.default(obj)

class ToolMap(object):

    __slots__ = ['_toolMap', '_fallbacks', '_siteInfo']

    def __init__(self):
        self._toolMap = defaultdict(PatternIndex)
        self._fallbacks  = []

    def empty(self):
        return len(self._toolMap) == 0

    def __init__(self, toolMap):
        self._toolMap = toolMap

    def add(self, prop, pattern, time):
        toolMap[prop].add(time, pattern)

    @staticmethod
    def from_json_dict(jsonobj):

        props = jsonobj['toolMap']
        fallbacks = jsonobj['fallbacks']

        jsonobj.update(
            {prop: PatternIndex.from_json_dict(values) for prop, values in props.items()}
        )
        obj =  ToolMap(jsonobj)

        fallbacks = [ToolMap.from_json_dict(fb) for fb in fallbacks]
        
        for fallback in fallbacks:
            obj = obj.add_fallback(fallback)
            
        return obj

    def merge(self, other):
        self._toolMap = {k : self._toolMap[k].merge(other._toolMap[k])
                         for k in set(chain(self._toolMap.keys(),
                                            other._toolMap.keys())
                                      )
                         }
        
    def add_fallback(self, other_toolMap):
        if not other_toolMap.empty():
            self._fallbacks.append(other_toolMap)
        return self

    def match(self, editSummary):
        def _match(toolMap, editSummary):
            for prop, index in toolMap.keys():
                if index.match(editSummary):
                    return prop

        for toolMap in chain([self._toolMap, self._fallbacks]):
            prop = _match(toolMap, editSummary)
            if prop is not None:
                return prop

        return None
