import mysite.search.models

def bug_url2bug_id(url, BUG_URL_PREFIX):
    before, after = url.split(BUG_URL_PREFIX)
    return int(after)

def bug_id2bug_url(bug_id, BUG_URL_PREFIX):
    return BUG_URL_PREFIX + str(bug_id)

def get_remote_bug_ids_already_stored(BUG_URL_PREFIX):
    for bug in mysite.search.models.Bug.all_bugs.filter(
        canonical_bug_link__contains=BUG_URL_PREFIX):
        yield bug_url2bug_id(
            bug.canonical_bug_link, BUG_URL_PREFIX=BUG_URL_PREFIX)

def find_ctype_xml_form_number(forms):
    for n, form in enumerate(forms):
        try:
            value = form.get_value('ctype')
            if value == 'xml':
                return n
        except:
            pass
    raise ValueError, "Could not find the right form."
