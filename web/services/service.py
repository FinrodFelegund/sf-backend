from shared.webscrapping.scrapper import Scrapper
from web.models import Website


def get_or_refresh_website(user, url: str, html: str):
    text = Scrapper(html_content=html)()
    content_hash = Website.hash_content(text)

    website, created = Website.objects.get_or_create(
        user=user,
        url=url,
        defaults={'content': text, 'content_hash': content_hash}
    )

    if not created and website.content_hash != content_hash:
        website.content = text
        website.content_hash = content_hash
        website.summary = None
        website.save(update_fields=['content', 'content_hash', 'summary', 'updated_at'])

    return website

