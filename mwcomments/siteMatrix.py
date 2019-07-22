from .util import get_api
from pkg_resources import resource_string, resource_exists

# we want, dbname -> (url, lang)
class SiteMatrix(object):

    def __init__(self):
        if resource_exists(__name__, 'resources/wikimedia_sites.json'):
            wikimedia_sites = resource_string(__name__, 'resources/wikimedia_sites.json')
            self.wikimedia_sites = json.loads(wikimedia_sites.decode())

        else:

            api = get_api("https://en.wikipedia.org")
            site_matrix = api.get(action='sitematrix')['sitematrix']

            for i, data in site_matrix.items():
                if type(data) is not dict:
                    continue

                lang = data['code']

                for site_data in data['site']:
                    yield (site_data['dbname'], {'url': site_data['url'], 'lang': lang})

            for site_data in site_matrix['specials']:
                lang = site_data['lang']
                yield (site_data['dbname'],{'url':site_data['url'], 'lang':lang})

                # add wikidata manually
                wikimedia_sites = dict(gen_sitematrix(site_matrix))

            if os.path.exists("resources"):
                if not os.path.exists("resources/wikimedia_sites.json"):
                    json.dump(wikimedia_sites, open("resources/wikimedia_sites.json",'w'))

            self.wikimedia_sites = wikimedia_sites
 
    def __get__(key):
        return self.wikmedia_sites[key]
