import re
from itertools import product
import datetime


def convert(summary, siteInfo, dt=None):

    if dt is None:
        dt = datetime.datetime.now()
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    dollar_replace = re.compile(re.escape("\$") + "\d")
    gender_replace = re.compile(
        re.escape("\{\{") + "GENDER.*" + re.escape("\}\}"))

    if summary[-1] == '.':
        summary = summary[0:-1]

    summary = _apply_parser_functions(summary, siteInfo, dt)

    summary = dollar_replace.sub('(.*)', summary)
    summary = gender_replace.sub("(.*)", summary)

    # remove final periods
    return re.compile(r"(?:.*{0}.*)".format(summary))


def _apply_parser_functions(summary, siteInfo, dt):
    import wikitextparser as wtp

    def _apply_parser_function(pf):
        pf = pf
        new_args = [_apply_parser_functions(arg.value, siteInfo, dt)
                    for arg in pf.arguments]

        if pf.name in wikitemplate_patterns:
            evaled_func = wikitemplate_patterns[pf.name.lower()](new_args)
            return evaled_func
        else:
            print("unknown parser function:{0}".pf.name)
            return re.escape(pf.string.strip())

    def ifexpr(new_args):
        cond, op1, op2 = new_args
        return r'(?:{0}|{1})'.format(op1, op2)

    def invoke(new_args):
        return ""

    def gender(new_args):
        t, a, b, c = new_args
        return r'(?:{0}|{1}|{2})'.format(a, b, c)

    # special pages can probably be had from the siteinfo api too.
    # one problem might be that the siteinfo falls out of date.
    def special(new_args):
        page_name = new_args[0]
        page_name = page_name.replace("\\", "")
        localized_namespaces = siteInfo.lookup_localized_namespace(-1, dt)
        prefixes = set(siteInfo.special_prefixes)

        # sorting just for reproducibility
        prefixes = sorted(prefixes.union(localized_namespaces))

        page_names = siteInfo.special_aliases[page_name]

        possible_values = ["{0}:{1}".format(a, b)
                           for a, b in product(prefixes, page_names)]

        return r'(?:{0})'.format('|'.join(possible_values))

    # TODO we need to handle localiztion templates using the api by passing in the url and the date.
    # NS can be got from the siteinfo api
    # we'll need to look up the namespace from git.
    def ns(new_args):
        # get langs from siteinfos
        # pass in the date in siteinfo
        namespace_name = new_args[0]
        namespace_name = namespace_name.replace("\\", "")
        local_ns_names = siteInfo.lookup_localized_namespace(
            namespace_name, dt)
        regex = r'(?:{0})'.format('|'.join(local_ns_names))
        return regex

    wikitemplate_patterns = {"#ifexpr": ifexpr, "#invoke": invoke,
                             "ns": ns, 'gender': gender, "#special": special}

    parsed = wtp.parse(summary)

    parser_functions = parsed.parser_functions

    # parser functions can be nested so let's evaluate them from shortest to longest.

    if len(parser_functions) > 0:

        pf = parser_functions[0]
        evaled_func = _apply_parser_function(pf)
        span = pf.span
        summary = re.escape(summary[0:span[0]]) + evaled_func + \
            _apply_parser_functions(summary[span[1]:], siteInfo, dt)

        return summary

    else:
        return re.escape(summary)
