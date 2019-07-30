import os
from util import get_api
from pkg_resources import resource_string, resource_exists
import json

from collections import namedtuple

# we want, dbname -> (url, lang)
SiteListItem = namedtuple('SiteList',['dbname','url'])
class SiteList():

    def __init__(self):
        if resource_exists(__name__, 'resources/wikimedia_sites.json'):
            wikimedia_sites = resource_string(__name__, 'resources/wikimedia_sites.json')
            self.wikimedia_sites = json.loads(wikimedia_sites.decode())

        else:
            self.wikimedia_sites = list(SiteList.from_api())

        if os.path.exists("resources"):
            if not os.path.exists("resources/wikimedia_sites.json"):
                json.dump(wikimedia_sites,
                          open("resources/wikimedia_sites.json",
                               'w'))

    def from_api(self):
        api = get_api("https://en.wikipedia.org")
        site_matrix = api.get(action='sitematrix')['sitematrix']

        for i, data in site_matrix.items():
            if type(data) is not dict:
                continue

            for site_data in data['site']:
                yield SiteListItem(dbname=site_data['dbname'],
                                   url=site_data['url'])

            for site_data in site_matrix['specials']:
                yield SiteListItem(dbname=site_data['dbname'],
                                   url=site_data['url'])

                
