import json
import logging
import re

from django.db.models import Count

from shared.llm.openai import (
    EmptyCompletionError,
    PromptLanguage,
    PromptType,
    get_openai_client,
)
from web.models import Entity, Relation, RelationType, Sentence, Website

logger = logging.getLogger(__name__)

_BATCH_SIZE = 20
_MAX_LABEL_LENGTH = 255
_MAX_ENTITIES_PER_SENTENCE = 8

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
    
    def _build_payload(self, sentences: list[Sentence]):
        payload = []
        sentences_by_id: dict[int, Sentence] = {}
        entities_by_sentence: dict[int, dict[int, Entity]] = {}

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
    
    def _build_message(self, batch: list[dict]):
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

            sentence = sentences_by_id.get(item.get('sentence_id'))
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
            relation, created = Relation.objects.get_or_create(
                user=self.user,
                entity1=e1,
                entity2=e2,
                relation_type=relation_type,
            )

            if created:
                placeholder = Relation.objects.filter(
                    user=self.user, entity1=e1, entity2=e2, relation_type__isnull=True
                ).first()

            if placeholder is not None:
                relation.websites.add(*placeholder.website.all())
                relation.sentences.add(*placeholder.sentences.all())
                placeholder.delete()

            relation.websites.add(self.website)
            relation.sentences.add(sentence)
            sentences = relation.sentences.all()
            links.append({
                'id': relation.id,
                'sentences': [sent.text for sent in sentences],
                'relation_type': relation_type.label,
                'source': str(e1.id),
                'target': str(e2.id),
            })

        return links

    def _persist_occurences(self, sentences_by_id, entities_by_sentence):
        candidate_ids = {
            entity_id
            for entities in entities_by_sentence.values()
            for entity_id in entities
        }
        if not candidate_ids:
            return []

        # any pair that already has a relation — labelled or not, from any page —
        # needs no placeholder
        linked = set(
            Relation.objects
            .filter(user=self.user, entity1_id__in=candidate_ids, entity2_id__in=candidate_ids)
            .values_list('entity1_id', 'entity2_id')
        )

        links = []

        for sentence_id, entities in entities_by_sentence.items():
            ids = sorted(entities)

            if len(ids) > _MAX_ENTITIES_PER_SENTENCE:
                logger.debug(
                    'Skipping co-occurrence for sentence %s: %s entities', sentence_id, len(ids)
                )
                continue

            sentence = sentences_by_id[sentence_id]

            for index, first_id in enumerate(ids):
                for second_id in ids[index + 1:]:
                    if (first_id, second_id) in linked:
                        continue

                    relation, _ = Relation.objects.get_or_create(
                        user=self.user,
                        entity1_id=first_id,
                        entity2_id=second_id,
                        relation_type=None,
                    )
                    linked.add((first_id, second_id))

                    relation.websites.add(self.website)
                    relation.sentences.add(sentence)

                    links.append({
                        'id': relation.id,
                        'sentences': [sent.text for sent in relation.sentences.all()],
                        'relation_type': None,
                        'source': str(first_id),
                        'target': str(second_id),
                    })

        return links        


    def stream(self):
        sentences = self._get_candidate_sentences()
        payload, sentences_by_id, entities_by_sentence = self._build_payload(sentences)
        if not payload:
            return
        
        for i in range(0, len(payload), _BATCH_SIZE):
            batch = payload[i:i + _BATCH_SIZE]

            try:
                raw = self.client.response(messages=self._build_message(batch))
            except EmptyCompletionError:
                logger.warning('No relations returned for batch %s of %s', i // _BATCH_SIZE, self.website.pk)
                continue
                
            extracted = self._parse_response(raw)
            yield self._persist(extracted, sentences_by_id, entities_by_sentence)
   
        cooccurences = self._persist_occurences(sentences_by_id, entities_by_sentence)
        if cooccurences:
            yield cooccurences


    def respond(self):
        return list(self.stream())