import pickle
import os
from util import get_api
from pkg_resources import resource_string, resource_exists
import json
from collections import namedtuple

# we want, dbname -> (url, lang)
SiteListItem = namedtuple('SiteList',['dbname','url'])
class SiteList():
    resource_path = 'resources/wikimedia_sites.pickle'

    def __init__(self):
        if resource_exists(__name__, 'resources/wikimedia_sites.json'):
            wikimedia_sites = resource_string(__name__, SiteList.resource_path)
            self.wikimedia_sites = pickle.loads(wikimedia_sites)

        else:
            self.wikimedia_sites = list(SiteList.from_api())

        if os.path.exists("resources"):
            if not os.path.exists(SiteList.resource_path):
                pickle.dump(self.wikimedia_sites,
                          open("resources/wikimedia_sites.pickle",
                               'wb'))

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
