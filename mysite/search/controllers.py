import mysite.search.models
import mysite.search.views
import collections
import urllib
import re
from django.db.models import Q

class Query:
    
    def __init__(self, terms, active_facets=None, terms_string=None): 
        self.terms = terms
        # FIXME: Change the name to "active facets".
        self.active_facets = active_facets or {}
        self._terms_string = terms_string

    @property
    def terms_string(self):
        if self._terms_string is None:
            raise ValueError
        return self._terms_string 

    @staticmethod
    def split_into_terms(string):
        # We're given some query terms "between quotes"
        # and some glomped on with spaces.
        # Strategy: Find the strings validly inside quotes, and remove them
        # from the original string. Then split the remainder (and probably trim
        # whitespace from the remaining terms).
        # {{{
        ret = []
        splitted = re.split(r'(".*?")', string)

        for (index, word) in enumerate(splitted):
            if (index % 2) == 0:
                ret.extend(word.split())
            else:
                assert word[0] == '"'
                assert word[-1] == '"'
                ret.append(word[1:-1])

        return ret
        # }}}

    @staticmethod
    def create_from_GET(GET):
        possible_facets = ['language', 'toughness']

        active_facets = {}
        for facet in possible_facets:
            if GET.get(facet):
                active_facets[facet] = GET.get(facet)
        terms_string = GET.get('q', '')
        terms = Query.split_into_terms(terms_string)

        return Query(terms=terms, active_facets=active_facets, terms_string=terms_string)

    def get_bugs_unordered(self):
        return mysite.search.models.Bug.open_ones.filter(self.get_Q())

    def __nonzero__(self):
        if self.terms or self.active_facets:
            return 1
        return 0

    def get_Q(self, exclude_these_facets=()):
        """Get a Q object which can be passed to Bug.open_ones.filter()"""

        # Begin constructing a conjunction of Q objects (filters)
        q = Q()

        if self.active_facets.get('toughness', None) == 'bitesize':
            q &= Q(good_for_newcomers=True)

        if 'language' in self.active_facets and 'language' not in exclude_these_facets:
            q &= Q(project__language__iexact=self.active_facets['language'])

        for word in self.terms:
            whole_word = "[[:<:]]%s[[:>:]]" % (
                    mysite.base.controllers.mysql_regex_escape(word))
            terms_disjunction = (
                    Q(project__language__iexact=word) |
                    Q(title__iregex=whole_word) |
                    Q(description__iregex=whole_word) |

                    # 'firefox' grabs 'mozilla fx'.
                    Q(project__name__iregex=whole_word)
                    )
            q &= terms_disjunction

        return q

    def get_possible_facets(self):

        filter_just_on_terms = self.get_Q(exclude_these_facets=('language',))
        bugs = mysite.search.models.Bug.open_ones.filter(filter_just_on_terms)

        if not bugs:
            return {}
        
        bitesize_get_parameters = dict(self.active_facets)
        bitesize_get_parameters.update({
            'q': self.terms_string,
            'toughness': 'bitesize',
            })
        bitesize_query_string = urllib.urlencode(bitesize_get_parameters)
        bitesize_count = 0
        bitesize_option = {'name': 'bitesize', 'count': bitesize_count,
                'query_string': bitesize_query_string}

        all_languages = {
                'name': 'all',
                'count': bugs.count(),
                # FIXME: we'll need more constraints when # of active_facets > 1.
                'query_string': urllib.urlencode({'q': self.terms_string})
                }

        possible_facets = { 
                # The languages facet is based on the project languages, "for now"
                'language': {
                    'name_in_GET': "language",
                    'sidebar_name': "by main project language",
                    'description_above_results': "projects primarily coded in %s",
                    'options': [all_languages],
                    },
                'toughness': {
                    'name_in_GET': "toughness",
                    'sidebar_name': "by toughness",
                    'description_above_results': "where toughness = %s",
                    'options': [bitesize_option]
                    }
                }


        distinct_language_columns = bugs.values('project__language').distinct()
        languages = [x['project__language'] for x in distinct_language_columns]
        for lang in sorted(languages):

            lang_get_parameters = dict(self.active_facets)
            lang_get_parameters.update({
                'q': self.terms_string,
                'language': lang,
                })
            lang_query_string = urllib.urlencode(lang_get_parameters)

            possible_facets['language']['options'].append({
                'name': lang,
                'count': bugs.filter(project__language=lang).count(),
                'query_string': lang_query_string
                })

        return possible_facets