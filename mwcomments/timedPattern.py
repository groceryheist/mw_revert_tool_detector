class TimedPattern(namedtuple('timedPattern', ['time', 'pattern'])):

    @staticmethod
    def from_elements(time, pattern, site_info):
        if not isinstance(time, datetime):
            time = fromisoformat(time)

        if not isinstance(pattern, re.Pattern):
            pattern = TimedPattern.to_regex(pattern, site_info)

        return TimedPattern(time, pattern)

    @staticmethod
    def to_regex(summary, site_info):

        dollar_replace = re.compile(re.escape("\$") + "\d")
        gender_replace = re.compile(re.escape("\{\{") + "GENDER.*" + re.escape("\}\}"))

        if summary[-1] == '.':
            summary = summary[0:-1]

        summary = TimedPattern.apply_parser_functions(summary, site_info)

        summary = dollar_replace.sub('(.*)', summary)
        summary = gender_replace.sub("(.*)", summary)

        # remove final periods
        return re.compile(r"(?:.*{0}.*)".format(summary))


    @staticmethod
    def apply_parser_functions(summary, site_info):

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
            api = get_api(site_info['url'])
            result = api.get(action='query', meta='siteinfo', siprop = ['magicwords'])
            special_aliases = chain(* [x['aliases'] for x in result['query']['magicwords'] if  x['name'] == 'special'])
            regex = r'(?:{0})'.format('|'.join(special_aliases))
            return regex


        def extractLocalizedNamespaces(lang, date):
            def get_relevant_commits(lang, date):
                commits = repo.iter_commits("master",[msgs_php_fh])
                commits_prior_to_date = [c for c in commits if c.committed_datetime <= date]
                return commits_prior_to_date[-2:]

            def convert_php_dict(php_dict):
                elems = php_dict.split(',')
                return {a.strip():b.strip().replace("'","") for a,b in [e.split("=>")[0:2] for e in elems if '=>' in e]}

            def parse_localized_namespaces(filehandle):
                php_code = open(filehandle).read()

                namespace_regex = re.compile(r"\$namespaceNames\s*=\s*\[(.*?)\];", flags = re.S)
                
                php_dict = namespace_regex.findall(php_code)[0]

                namespace_dict = convert_php_dict(php_dict)
                return namespace_dict


            import git
            repo_path = "temp/mediawiki"
            repo = git.Repo(repo_path)
            lang = lang[0].upper() + lang[1:]
            msgs_php_fh = os.path.join("languages","Messages{0}.php".format(lang))


            commits = get_relevant_commits(lang, date)


            for commit in commits:
                repo.git.checkout('-f', commit)
                yield (parse_localized_namespaces(os.path.join(path,msgs_php_fh)))

        # TODO we need to handle localiztion templates using the api by passing in the url and the date.
        # NS can be got from the siteinfo api
        # we'll need to look up the namespace from git. 
        def ns(pf):
            # get langs from siteinfos
            # pass in the date in siteinfo

            namespace_dicts = extractLocalizedNamespaces(lang,date)
            namespace_name = pf.

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
