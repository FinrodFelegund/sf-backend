import spacy
from langdetect import detect
import json

class NERPipeline:
    def __init__(self, document: str):
        self._document = document
        self._lang = ""
        self._pipe = None
        self._tags = ['PERSON', 'ORG', 'GPE', 'LOC', 'NORP']

    def detect_language(self):
        lang = detect(self._document)

        if(lang.startswith('en')):
            return 'en'
        
        return 'de'
    
    def set_language(self, lang):
        self._lang = lang

    def set_spacy_pipeline(self):
        if self._lang == 'en':
            self._pipe = spacy.load(name='en_core_web_md')
        elif self._lang == 'de':
            self._pipe = spacy.load(name='de_core_news_md')

    def ensure_sentencizer(self):
        try:
            if 'parser' not in self._pipe.pipe_names and 'senter' not in self._pipe.pipe_names:
                self._pipe.add_pipe('sentencizer')
        except Exception:
            pass

    def is_valid_entity(self, tag: str):
        return True if tag in self._tags else False

    def extract_entities(self):
        doc = self._pipe(self._document)
        entities = {}
        sentences = []

        for sent_idx, sent in enumerate(doc.sents):
            ents = []
            for ent in sent.ents:
                label = ent.label_
                if not self.is_valid_entity(label):
                    continue
                ents.append(ent)
                if ent not in entities:
                    entities[ent.text] = {
                        'label': label,
                        'caption': ent.text,
                        'count': 1,
                        'sent_idx': [sent_idx]
                    }
                else:
                    entities[ent]['count'] += 1
                    entities[ent]['sent_idx'].append(sent_idx)

            sentence = sent.text.strip()
            tokens = []
            for token_idx, token in enumerate(sent):
                for ent in ents:
                    if token.idx >= ent.start_char and token.idx < ent.end_char:
                        break
                tokens.append({
                    'index': token_idx + 1,
                    'word': token.text,
                })
            
            sentences.append({
                'index': sent_idx,
                'tokens': tokens,
                'text': sentence,
            })
        
        output = {
            'entities': entities,
            'sentences': sentences
        }

        return json.dumps(output, indent=4)




    def __call__(self):
        lang = self.detect_language()
        if lang != self._lang:
            self.set_language(lang)
            self.set_spacy_pipeline()

        self.ensure_sentencizer()

        return self.extract_entities()







