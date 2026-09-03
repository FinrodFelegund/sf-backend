import trafilatura 
from trafilatura.metadata import extract_metadata
import re

class Scrapper:
    
    def __init__(self, html_content):
        self._html_content = html_content

    def __call__(self):
        result = trafilatura.extract(self._html_content)
        if not result:
            return ''
        
        return result

    def title(self):
        try:
            meta = extract_metadata(self._html_content, extensive=False)
            if meta is not None and meta.title:
                return re.sub(r'\s+', ' ', meta.title).strip()[:500]
        
        except Exception:
            pass

        match = re.search(
            r'<title[^>]*>(.*?)</title>', self._html_content or '', re.IGNORECASE | re.DOTALL
        )

        if match:
            return re.sub(r'\s+', ' ', match.group(1)).strip()[:500]

        return ''