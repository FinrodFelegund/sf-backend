from storyfinder.models import BaseModel
from django.db import models

from user.models import CustomUser

# Create your models here.

class Website(BaseModel):
    """Model representing a website"""
    
    url = models.TextField(help_text='URL of the website', unique=True)
    content = models.TextField(help_text='Scrapped and normalized content of the website')

    class Meta:
        ordering = ['url', 'content']
        verbose_name = 'Website'
        verbose_name_plural = 'Websites'

    def __str__(self):
        return f'Web URL: {self.url}, ID: {self.id}'

class Sentence(BaseModel):
    """Model representing a specific sentence from a website"""
    site = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='sentences')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sentences')
    text = models.TextField()

    class Meta:
        ordering = ['user', 'site', 'created_at']
        verbose_name = 'Sentence'
        verbose_name_plural = 'Sentences'

    def __str__(self):
        return f'{self.site.url} {self.user.username}'

class Entity(BaseModel):
    """Model representing a specific named entity inside a website"""
    site = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='entities')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='entities')
    entity_name = models.CharField(max_length=30)
    entity_type = models.CharField(max_length=5)

    sites = models.ManyToManyField(Website)
    sentences = models.ManyToManyField(Sentence)

    class Meta:
        ordering = ['user', 'site', 'created_at']
        verbose_name = 'Entity'
        verbose_name_plural = "Entities"

    def __str__(self):
        return f'{self.entity_name} {self.entity_type}'

class RelationType(BaseModel):
    """Model representing a specific Relation Type as generated my a NLP Model"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='relationtypes')
    label = models.TextField()

    class Meta:
        ordering = ['user', 'label', 'created_at']
        verbose_name = 'Relation Type'
        verbose_name_plural = 'Relation Types'

    def __str__(self):
        return f'{self.label}'

class Relation(BaseModel):
    """Model representing a relation between two entities from a website"""
    entity1 = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='relationsource')
    entity2 = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='relationtarget')
    relation_type = models.ForeignKey(RelationType, on_delete=models.CASCADE)
    sentences = models.ManyToManyField(Sentence)

    class Meta:
        ordering = ['entity1', 'entity2', 'relation_type']
        verbose_name = 'Relation'
        verbose_name_plural = 'Relations'

