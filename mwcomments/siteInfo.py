import os
from json import JSONEncoder
from itertools import chain
from .util import get_api

class SiteInfoEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SiteInfo):
            return obj.to_dict()
        else:
            return JSONEncoder.default(obj)

class SiteInfo(object):
    __slots__ = ['SiteInfo', 'url', 'langcode', '_msgs_php_files',
                 'local_namespaces_byname', 'namespaces_byid',
                 'special_aliases', 'fallback_langs',
                 'special_prefixes', 'canonical_namespaces_byid',
                 'canonical_namespaces_byname', 'lang_variants',
                 'toolMap', 'have_info']

    def __init__(self, url):
        self.url = url
        api = get_api(self.url)
        self.have_info = self._lookup_siteinfo(api)
        if not self.have_info:
            return None

        if self.lang_variants is None:
            langSuffixes = [self.langcode[0].upper() + self.langcode[1:]]
        else:
            langSuffixes = (langcode[0].upper() + langcode[1:]
                            for langcode in
                            set(self.lang_variants + [self.langcode]))
            langSuffixes = [ls.replace("-", "_") for ls in langSuffixes]

        self._msgs_php_files = [
            os.path.join("languages",
                         "messages",
                         "Messages{0}.php".format(langSuffix))
            for langSuffix in langSuffixes]

        # this structure is going to map from ns_id -> pairedSortedList

    def _lookup_siteinfo(self, api):
        from mwapi.errors import APIError
        try:
            result = api.get(action='query',
                             meta='siteinfo',
                             siprop=['general',
                                     'namespaces',
                                     'specialpagealiases',
                                     'magicwords'])

        except APIError as e:
            print(e)
            return None

        except ValueError as e:
            print(e)
            return

        except Exception as e:
            print(e)
            return

        general = result['query']['general']

        self.langcode = general['lang']

        if "fallback" in general:
            self.fallback_langs = list(chain(* [[code
                                                 for _, code
                                                 in fb.items()]
                                                for fb in
                                                general['fallback']]))
        else:
            self.fallback_langs = None

        self.local_namespaces_byname = {value['*']: int(value['id'])
                                        for value
                                        in result['query']['namespaces'].values()
                                        if '*' in value}

        if 'variants' in general:
            self.lang_variants = [d['code'] for d in general['variants']]

        else:
            self.lang_variants = None

        self.namespaces_byid = {v: k for k,
                                v in self.local_namespaces_byname.items()}

        res_namespaces = result['query']['namespaces'].values()

        self.canonical_namespaces_byid = {
            int(value['id']): value['canonical']
            for value
            in res_namespaces
            if 'canonical' in value}

        self.canonical_namespaces_byname = {
            value['canonical'].lower(): int(value['id'])
            for value
            in res_namespaces
            if 'canonical' in value}

        self.special_aliases = {
            value['realname']: value['aliases']
            for value
            in result['query']['specialpagealiases']}

        magicwords = result['query']['magicwords']
        special_prefixes = set([pair['aliases']
                                for pair
                                in magicwords if
                                pair['name'] == 'special'][0])

        special_prefixes.add(self.namespaces_byid[-1])
        special_prefixes.add(self.canonical_namespaces_byid[-1])
        self.special_prefixes = sorted(special_prefixes)
        return True

    def lookup_localized_namespace(self, ns, datetime):

        try:
            ns = int(ns)
            is_int = True
        except ValueError:
            is_int = False

        if is_int:
            result = self.lookup_localized_namespace_byid(ns, datetime)
        else:
            result = self.lookup_localized_namespace_byname(ns, datetime)

        return sorted(set(result))

    def lookup_localized_namespace_byname(self, ns_name, datetime):
        key = ns_name.lower().replace('-', ' ').replace('_', ' ')
        ns_id = self.local_namespaces_byname.get(key, None)
        if ns_id is None:
            ns_id = self.canonical_namespaces_byname[key.lower()]
        return self.lookup_localized_namespace_byid(ns_id, datetime)

    def lookup_localized_namespace_byid(self, ns_id, datetime):
        return (d[ns_id] for d
                in self._extractLocalizedNamespaces(datetime)
                if d is not None)

    def _extractLocalizedNamespaces(self, date):
        import git
        from .util import parse_localized_namespaces

        repo_path = "temp/mediawiki"
        repo = git.Repo(repo_path)

        def _extract_from_filehistory(msgs_php_file):
            commits = repo.iter_commits(
                "master", [msgs_php_file], max_age=date, max_count=2)

            for commit in commits:
                repo.git.checkout('-f', commit)

                ns_dict = parse_localized_namespaces(
                    os.path.join(repo_path, msgs_php_file))

                yield ns_dict

            # get the relevant commits

        return chain(* (_extract_from_filehistory(msgs_php_file) for msgs_php_file in self._msgs_php_files))
