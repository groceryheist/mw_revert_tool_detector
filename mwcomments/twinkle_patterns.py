import mwapi
import re
from itertools import chain
from mwcomments.util import get_api

# wikis without twinkle: ru, eu, esbooks, esquote, fi, he, sq, it, bs, cs, et, pl, hu, 

new_twinkle_page = "MediaWiki:Gadget-Twinkle.js"

url = 'https://fr.wikipedia.org'

## 1. look for the MediaWiki:Gadget_Twinkle.js page
## 2. if we find it then find then look for TwinkleConfig.summaryAd or summaryAd variables. See what they get set to and use that. 

def find_summary_ad(url):
    
    summaryAdPattern = re.compile(r'^.*summaryAd\ ?[:=]\ ?[\"\']\ ?(.*)\ ?[\"\'][,;].*$',flags=re.M)

    def check_prod_summary_ad(url):
        api = get_api(url)
        
        result = api.get(action='query',
                         list='search',
                         srsearch='summaryAd',
                         srnamespace=[2,8],
                         srwhat='text',
                         srlimit='max')

        prod_pages = [r for r in result['query']['search'] if r['title'].lower().endswith("twinkleprod.js") or r['title'].lower().endswith("common.js") or r['title'].lower().endswith("twinkle.js")]

        contents = []
        for page in prod_pages:
            page_revisions = api.get(action='query',
                                     prop='revisions',
                                     rvprop=['ids','timestamp','comment','user','content'],
                                     pageids=[page['pageid']],
                                     rvlimit='max')
            if isinstance(page_revisions['query']['pages'],dict):
                contents.extend([r["*"]
                                 for r in chain(*
                                                [p['revisions'] for pageid, p in page_revisions['query']['pages'].items()])])
            
        captures = list(chain(*[summaryAdPattern.findall(c) for c in contents]))
        counted = [(x,captures.count(x)) for x in captures]
        if len(counted) > 0:
            return max(counted, key=lambda t:t[1])[0]

    def check_gadget_summary_ad(url):
        api = get_api(url)

        result = api.get(action='query',
                         prop='revisions',
                         rvprop=['ids','timestamp','comment','user','content'],
                         titles=['Mediawiki:Gadget-Twinkle.js'],
                         rvlimit='max')


        pages = [p for pid, p in result['query']['pages'].items()]
        contents = [r['*'] for r in chain(*
                                          [p['revisions'] for p in pages if 'revisions' in p])]


        captures = list(chain(*[summaryAdPattern.findall(c) for c in contents]))
        counted = list(set([(x,captures.count(x)) for x in captures]))
        if counted and len(counted) > 0: 
            return max(counted, key=lambda t:t[1])[0]

    from_gadget = check_gadget_summary_ad(url)
    if from_gadget:
        return from_gadget
    else:
        return check_prod_summary_ad(url)
