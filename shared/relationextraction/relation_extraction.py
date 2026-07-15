import json, re
from typing import Dict, List

from django.db.models import Count

from shared.llm.openai import get_openai_client, PromptType, PromptLanguage
from web.models import Website, Sentence, Entity, Relation, RelationType

_BATCH_SIZE = 20
_MAX_LABEL_LENGTH = 255

class RelationExtraction:
    
    def __init__(self, user, website: Website):
        self.user = user
        self.website = website
        self.client = get_openai_client()

    def _get_candidate_sentences(self):
        return list(
            Sentence.objects.filter(website=self.website)
            .annotate(entity_count=Count('entities'))
            .filter(entity_count__gte=2)
            .prefetch_related('entities')
        )
    
    def _build_payload(self, sentences: List[Sentence]):
        payload = []
        sentences_by_id: Dict[int, Sentence] = {}
        entities_by_sentence: Dict[int, Dict[int, Entity]] = {}

        for sentence in sentences:
            entities = [e for e in sentence.entities.all() if e.user_id == self.user.id]
            if len(entities) < 2:
                continue

            sentences_by_id[sentence.id] = sentence
            entities_by_sentence[sentence.id] = {
                e.id: e for e in entities
            }

            payload.append({
                'sentence_id': sentence.id,
                'text': sentence.text,
                'entities': [
                    {'id': e.id, 'name': e.entity_name, 'type': e.entity_type}
                    for e in entities
                ],
            })
        
        return payload, sentences_by_id, entities_by_sentence
    
    def _build_message(self, batch: List[Dict]):
        prompt = self.client.get_active_prompt(
            prompt_type=PromptType.GRAPH,
            lang=PromptLanguage.EN,
        )

        return [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': json.dumps(batch, ensure_ascii=False)}
        ]
    
    @staticmethod
    def _parse_response(raw: str):
        if not raw:
            return []
        # strip all the stuff away the modle might have haded like md tags etcc
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return []
        
        relations = data.get('relations') if isinstance(data, dict) else None
        return relations if isinstance(relations, list) else []
    
    def _persist(self, extracted, sentences_by_id, entities_by_sentence):
        links = []
        for item in extracted:
            if not isinstance(item, dict):
                continue

            sentence = sentences_by_id.get((item.get('sentence_id')))
            if sentence is None:
                continue

            allowed = entities_by_sentence.get(sentence.id, {})
            e1 = allowed.get(item.get('entity1_id'))
            e2 = allowed.get(item.get('entity2_id'))
            label = (item.get('label') or '').strip().lower()[:_MAX_LABEL_LENGTH]

            if e1 is None or e2 is None or e1.id == e2.id or not label:
                continue

            if e1.id > e2.id:
                e1, e2 = e2, e1

            relation_type, _ = RelationType.objects.get_or_create(user=self.user, label=label)
            relation, _ = Relation.objects.get_or_create(
                user=self.user,
                entity1=e1,
                entity2=e2,
                relation_type=relation_type,
            )

            relation.sentences.add(sentence)
            links.append({
                'id': relation.id,
                'sentence': sentence.text,
                'relation_type': relation_type.label,
                'source': str(e1.id),
                'target': str(e2.id),
            })

        return links


    def stream(self):
        sentences = self._get_candidate_sentences()
        payload, sentences_by_id, entities_by_sentence = self._build_payload(sentences)
        if not payload:
            return
        
        for i in range(0, len(payload), _BATCH_SIZE):
            batch = payload[i:i+_BATCH_SIZE]
            raw = self.client.response(messages=self._build_message(batch))
            extracted = self._parse_response(raw)
            yield self._persist(extracted, sentences_by_id, entities_by_sentence)
   


    def respond(self):
        return list(self.stream())