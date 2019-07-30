import re
from itertools import product
import datetime

def convert(summary, siteInfo, dt= None):

    if dt is None:
         dt = datetime.datetime.now()
         dt = dt.replace(tzinfo=datetime.timezone.utc)
    dollar_replace = re.compile(re.escape("\$") + "\d")
    gender_replace = re.compile(re.escape("\{\{") + "GENDER.*" + re.escape("\}\}"))

    if summary[-1] == '.':
        summary = summary[0:-1]

    summary = _apply_parser_functions(summary, siteInfo, dt)

    summary = dollar_replace.sub('(.*)', summary)
    summary = gender_replace.sub("(.*)", summary)

    # remove final periods
    return re.compile(r"(?:.*{0}.*)".format(summary))

def _apply_parser_functions(summary, siteInfo, dt):

    import wikitextparser as wtp
    parsed = wtp.parse(summary)

    parser_functions = parsed.parser_functions

    def ifexpr(pf):
        cond, op1, op2 = pf.arguments
        return r'(?:{0}|{1})'.format(re.escape(op1.value), re.escape(op2.value))

    def invoke(pf):
        t, func, op = pf.arguments
        if t[0].parent().name == '#ifexpr':
            return ""

    def gender(pf):
        t, a, b, c = pf.arguments
        return r'(?:{0}|{1}|{2})'.format(re.escape(a), re.escape(b), re.escape(c))

    # special pages can probably be had from the siteinfo api too.
    # one problem might be that the siteinfo falls out of date.
    def special(pf):
        page_name = pf.arguments[0].value
        localized_namespaces = siteInfo.lookup_localized_namespace(-1, dt)
        prefixes = set(siteInfo.special_prefixes)

        #sorting just for reproducibility
        prefixes = sorted(prefixes.union(localized_namespaces))

        page_names = siteInfo.special_aliases[page_name]

        possible_values = ["{0}:{1}".format(a,b) for a, b in product(prefixes, page_names)]

        return r'(?:{0})'.format('|'.join(possible_values))


    # TODO we need to handle localiztion templates using the api by passing in the url and the date.
    # NS can be got from the siteinfo api
    # we'll need to look up the namespace from git. 
    def ns(pf):
        # get langs from siteinfos
        # pass in the date in siteinfo
        namespace_name = pf.arguments[0].value
        local_ns_names = siteInfo.lookup_localized_namespace(namespace_name, dt)
        regex= r'(?:{0})'.format('|'.join(local_ns_names))
        return regex

    wikitemplate_patterns = {"#ifexpr": ifexpr, "#invoke": invoke, "ns":ns, 'gender':gender, "#special":special}

    if len(parser_functions) > 0:

        pf = parser_functions[0]
        span = pf.span
        if pf.name in wikitemplate_patterns:
            evaled_func = wikitemplate_patterns[pf.name.lower()](pf)
            summary = re.escape(summary[0:span[0]]) + evaled_func + re.escape(summary[span[1]:])
            return summary

    else:
        return re.escape(summary)
