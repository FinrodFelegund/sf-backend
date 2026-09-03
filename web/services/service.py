from django.db.models import Count, Sum

from shared.webscrapping.scrapper import Scrapper
from web.models import Website, WebsiteEntity


def get_or_refresh_website_with_state(user, url: str, html: str):
    scrapper = Scrapper(html_content=html)
    text = scrapper()
    title = scrapper.title()
    content_hash = Website.hash_content(text)

    website, created = Website.objects.get_or_create(
        user=user,
        url=url,
        defaults={'content': text, 'content_hash': content_hash, 'title': title}
    )

    if created:
        return website, True

    changed = []

    if title and website.title != title:
        website.title = title
        changed.append('title')
    
    content_is_new = website.content_hash != content_hash

    if content_is_new:
        website.content = text
        website.content_hash = content_hash
        website.summary = None
        changed += ['content', 'content_hash', 'summary']

    if changed:
        website.save(update_fields=changed + ['updated_at'])

    return website, content_is_new

def get_or_refresh_website(user, url: str, html: str):
    website, _ = get_or_refresh_website_with_state(user, url, html)
    return website

def tfidf_for_websites(user, website_ids):
    if not website_ids:
        return {}

    tf = dict(
        WebsiteEntity.objects
        .filter(entity__user=user, website_id__in=website_ids)
        .values('entity_id')
        .annotate(tf=Sum('count'))
        .values_list('entity_id', 'tf')
    )
    if not tf:
        return {}

    df = dict(
        WebsiteEntity.objects
        .filter(entity_id__in=list(tf.keys()), website__user=user)
        .values('entity_id')
        .annotate(df=Count('website', distinct=True))
        .values_list('entity_id', 'df')
    )

    raw = {eid: (count or 0) / max(df.get(eid, 1), 1) for eid, count in tf.items()}
    top = max(raw.values(), default=0.0)

    if top <= 0:
        return {str(eid): 0.0 for eid in raw}

    return {str(eid): value / top for eid, value in raw.items()}

