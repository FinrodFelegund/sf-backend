import logging
import re
from functools import lru_cache

import spacy
from langdetect import DetectorFactory, LangDetectException, detect

logger = logging.getLogger(__name__)

_EXCLUDED_COMPONENTS = ['tagger', 'parser', 'attribute_ruler', 'lemmatizer', 'morphologizer']

_MODELS_BY_LANG = {
    'en': 'en_core_web_md',
    'de': 'de_core_news_md',
}

_LANG_DETECTION_SIZE = 2000
_DEFAULT_LANG = 'de'
_MIN_ALPHA_CHARS = 20
_MAX_DOCUMENT_LENGTH = 200_000

VALID_ENTITY_TAGS = frozenset({'PERSON', 'ORG', 'GPE', 'LOC', 'NORP'})

def _has_letters(text: str, minimum: int) -> bool:
    seen = 0
    for char in text:
        if char.isalpha():
            seen += 1
            if seen >= minimum:
                return True
    return False

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

        if not _has_letters(sample, _MIN_ALPHA_CHARS):
            sample = self._document.strip()

        if not _has_letters(sample, _MIN_ALPHA_CHARS):
            return _DEFAULT_LANG

        try:
            lang = detect(sample) if sample else 'en'
        except LangDetectException:
            logger.info(
                'Language detection failed on %s characters; falling back to %s',
                len(sample), _DEFAULT_LANG,
            )
            return _DEFAULT_LANG
            
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



