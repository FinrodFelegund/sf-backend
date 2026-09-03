import spacy
from langdetect import detect
import re
from functools import lru_cache

_EXCLUDED_COMPONENTS = ['tagger', 'parser', 'attribute_ruler', 'lemmatizer', 'morphologizer']

_MODELS_BY_LANG = {
    'en': 'en_core_web_md',
    'de': 'de_core_news_md',
}

_LANG_DETECTION_SIZE = 2000
_MAX_DOCUMENT_LENGTH = 200_000

VALID_ENTITY_TAGS = frozenset({'PERSON', 'ORG', 'GPE', 'LOC', 'NORP'})

@lru_cache(maxsize=None)
def _load_pipeline(lang: str):
    nlp = spacy.load(_MODELS_BY_LANG[lang], exclude=_EXCLUDED_COMPONENTS)
    if 'parser' not in nlp.pipe_names and 'senter' not in nlp.pipe_names:
        nlp.add_pipe('sentencizer')
    return nlp

def preload_pipeline():
    for lang in _MODELS_BY_LANG:
        _load_pipeline(lang)

class NERPipeline:
    def __init__(self, document: str):
        self._document = document[:_MAX_DOCUMENT_LENGTH]

    def _detect_language(self):
        sample = self._document[:_LANG_DETECTION_SIZE].strip()
        lang = detect(sample) if sample else 'en'
        return 'en' if lang.startswith('en') else 'de'
    
    def normalize_entity(self, text: str) -> str:
        if not text:
            return ''
        t = text.strip()
        t = re.sub(r"^[\s'\"()\[\]{}/\\-]+", '', t)
        t = re.sub(r"[\s'\"()\[\]{}/\\.,;:!?-]+$", '', t)
        t = re.sub(r"\s+", ' ', t)
        return t.strip()
    
    def _extract(self, nlp: spacy.Language):
        doc = nlp(self._document)
        entities: dict[str, str] = {}
        sentences = []

        for sent_idx, sent in enumerate(doc.sents):
            for ent in sent.ents:
                if ent.label_ not in VALID_ENTITY_TAGS:
                    continue
                entry = entities.get(ent.text)
                if entry is None:
                    entities[ent.text] = {
                        'label': ent.label_,
                        'caption': self.normalize_entity(ent.text),
                        'count': 1,
                        'sent_idx': [sent_idx],
                    }
                else:
                    entry['count'] += 1
                    entry['sent_idx'].append(sent_idx)

            sentences.append({
                'index': sent_idx,
                'tokens': [{'index': i + 1, 'word': token.text} for i, token in enumerate(sent)],
                'text': sent.text.strip(),
            })

        return {'entities': entities, 'sentences': sentences}
    
    def __call__(self):
        nlp = _load_pipeline(self._detect_language())
        return self._extract(nlp)



