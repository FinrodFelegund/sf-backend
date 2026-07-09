from django.contrib import admin

# Register your models here.
from chat.models import ChatHistory, ChatSystemPrompt

@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'website', 'message_count', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['title', 'user__username', 'website']
    ordering = ['-updated_at', 'created_at']
    readonly_fields = ('created_at', 'updated_at')

    def message_count(self, obj):
        return len(obj.messages)
    
    message_count.short_description = 'Messages'


@admin.register(ChatSystemPrompt)
class ChatSystemPromptAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'lang', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'role']
    search_fields = ['name', 'content']
    ordering = ['-updated_at', 'created_at']
    readonly_fields = ('created_at', 'updated_at')
    fields = ('name', 'role', 'lang', 'content', 'is_active', 'created_at', 'updated_at')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['content'].widget.attrs['rows'] = 30
        form.base_fields['content'].widget.attrs['style'] = 'width 100%; font-family: monospace;'
        return form