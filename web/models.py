import hashlib
from django.db import models
from django.conf import settings
from user.models import CustomUser
from storyfinder.models import BaseModel


# Create your models here.
class Website(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='websites')
    url = models.TextField(help_text='URL of the website')
    content = models.TextField(help_text='Scraped and normalized content of the website')
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text='SHA-256 of content. Used to detect page changes and invalidate the cached summary.',
    )
    summary = models.TextField(
        null=True,
        blank=True,
        help_text='Rough LLM-generated sumary, used as chat context. Cleared when content_hash changes.',
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Website'
        verbose_name_plural = 'Websites'
        constraints = [
            models.UniqueConstraint(fields=['user', 'url'], name='unique_website_per_user'),
        ]

    def __str__(self):
        return f'{self.url} | {self.user.username}'
    
    @staticmethod
    def hash_content(content: str):
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


class Sentence(BaseModel):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='sentences')
    text = models.TextField()

    class Meta:
        ordering = ['website', 'created_at']
        verbose_name = 'Sentence'
        verbose_name_plural = 'Sentences'
        indexes = [models.Index(fields=['website'])]

    def __str__(self):
        return f'{self.website.url}: {self.text[:50]}'
    

class Entity(BaseModel):
    class EntityType(models.TextChoices):
        PERSON = 'PERSON', 'Person'
        ORG    = 'ORG', 'Organization'
        GPE    = 'GPE', 'Country/City/State'
        LOC    = 'LOC', 'Location'
        NORP   = 'NORP', 'Nationality/Religious/Political group'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='entities')
    entity_name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=30, choices=EntityType.choices)

    websites = models.ManyToManyField(Website, through='WebsiteEntity', related_name='entities')
    sentences = models.ManyToManyField(Sentence, related_name='entities')

    class Meta:
        ordering = ['user', 'entity_name']
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'
        constraints = [
            models.UniqueConstraint(fields=['user', 'entity_name', 'entity_type'], name='unique_entity_per_user'),
        ]

    def __str__(self):
        return f'{self.entity_name} ({self.entity_type})'
    
class WebsiteEntity(BaseModel):
    website = models.ForeignKey(Website, on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    count = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['website', 'entity'], name='unique_website_entity'),
        ]
        verbose_name = 'Website Entity Occurrence'
        verbose_name_plural = 'Website Entity Occurrences'

    def __str__(self):
        return f'{self.entity.entity_name} on {self.website.url} ({self.count}x)'


class RelationType(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='relation_types')
    label = models.CharField(max_length=255)

    class Meta:
        ordering = ['user', 'label']
        verbose_name = 'Relation Type'
        verbose_name_plural = 'Relation Types'
        constraints = [
            models.UniqueConstraint(fields=['user', 'label'], name='unique_relationtype_per_user'),
        ]

    def __str__(self):
        return self.label


class Relation(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='relations')
    entity1 = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='relations_as_first')
    entity2 = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='relations_as_second')
    relation_type = models.ForeignKey(RelationType, on_delete=models.CASCADE, null=True, blank=True)
    sentences = models.ManyToManyField(Sentence, related_name='relations')

    class Meta:
        ordering = ['user', 'entity1', 'entity2']
        verbose_name = 'Relation'
        verbose_name_plural = 'Relations'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'entity1', 'entity2', 'relation_type'], name='unique_relation_per_user'
            ),
        ]

    def save(self, *args, **kwargs):
        # Keep entity1/entity2 in a stable order so an undirected pair is never stored twice as (A,B) and (B,A)
        if self.entity1_id and self.entity2_id and self.entity1_id > self.entity2_id:
            self.entity1_id, self.entity2_id = self.entity2_id, self.entity1_id
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.relation_type.label if self.relation_type else '<no label>'
        return f'{self.entity1} -[{label}]- {self.entity2}'