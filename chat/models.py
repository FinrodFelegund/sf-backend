from django.db import models
from django.conf import settings


from datetime import datetime
from storyfinder.models import BaseModel
from web.models import Website


# Create your models here.

class ChatHistory(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_history')
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='chat_history')
    title = models.CharField(max_length=255, help_text='Title of the conversation', blank=True)
    messages = models.JSONField(default=list, help_text='Chat messages stored as JSON array')

    class Meta:
        ordering = ['-updated_at', '-created_at']
        verbose_name = 'Chat History'
        verbose_name_plural = 'Chat Histories'
        indexes = [models.Index(fields=['user', 'website'])]

    def __str__(self):
        return f'{self.user.username} - {self.title} | Messages: {len(self.messages)}'
    
    def generate_title(self):
        if not self.title:
            now = datetime.now()
            self.title = now.strftime('Chat %Y-%m-%d %H:%M')

    def save(self, *args, **kwargs):
        self.generate_title()
        super().save(*args, **kwargs)


class ChatSystemPrompt(BaseModel):
    ROLE_CHOICES = [
        ('chat', 'Chat'),
        ('summary', 'Summary'),
        ('graph', 'Graph')
    ]

    LANG_CHOICES = [
        ('eng', 'ENG'),
        ('ger', 'GER'),
    ]

    name = models.CharField(max_length=255, help_text='Descriptive name for the prompt')
    content = models.TextField(help_text='The system prompt text sent to the LLM')
    is_active = models.BooleanField(default=False, help_text='Only one prompt per role can be active at a time')
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='actor',
        help_text='Role this prompt serves: actor (chat bot) | summary (website summary)'
    )

    lang = models.CharField(
        max_length=5,
        choices=LANG_CHOICES,
        default='eng',
        help_text='Language of the prompt'
    )

    class Meta:
        verbose_name = 'Chat System Prompt'
        verbose_name_plural = 'Chat System Prompts'
        ordering = ['-is_active', '-updated_at']


    def save(self, *args, **kwargs):
        if self.is_active:
            ChatSystemPrompt.objects.exclude(pk=self.pk).filter(role=self.role, lang=self.lang).update()
        super().save(*args, **kwargs)

    def __str__(self):
        active_label = '[ACTIVE]' if self.is_active else ''
        return f'{self.name}|{self.lang}|{active_label}'
    
    

