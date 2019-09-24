import re
from itertools import chain
from mwcomments.util import get_api


def find_huggle_pattern(url):
    summary_pattern = re.compile(r"^\s?summary:\s?[\'\"](.*)[\'\"]$", flags = re.M)
    old_version_page = "Wikipedia:Huggle/Config"
    new_version_page = "Wikipedia:Huggle/Config.yaml"

    api = get_api(url)
    contents = []
    for title in [old_version_page,new_version_page]:
        result = api.get(action='query',
                         prop='revisions',
                         rvprop=['ids','timestamp','comment','user','content'],
                         titles=[title],
                         rvlimit=['max'],
                         redirects=True)

        if isinstance(result['query']['pages'],dict):
            contents.extend([r["*"]
                             for r in chain(*
                                            [p['revisions'] for pageid, p in result['query']['pages'].items()])])

    captures = list(chain(*[summary_pattern.findall(c) for c in contents]))
    counted = [(x,captures.count(x)) for x in captures]
    if len(counted) > 0:
        return max(counted, key=lambda t:t[1])[0]
