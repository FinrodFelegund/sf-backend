import trafilatura

class Scrapper():
    
    def __init__(self, html_content):
        self._html_content = html_content

    def __call__(self):
        return trafilatura.extract(self._html_content)