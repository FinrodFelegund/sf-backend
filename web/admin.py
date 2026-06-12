from django.contrib import admin
from web.models import Website, Sentence, Entity, Relation, RelationType

# Register your models here.

@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'content', 'created_at', 'updated_at')
    search_fields = ('url', )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'site', 'text', 'created_at', 'updated_at')
    search_fields = ('user', 'site')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('site', 'user', 'entity_name', 'entity_type', 'created_at', 'updated_at')
    search_fields = ('entity_name', 'entity_type')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Relation)
class RelationAdmin(admin.ModelAdmin):
    list_display = ('entity1', 'entity2', 'relation_type')
    search_fields = ('entity1', 'entity2', 'relation_type')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RelationType)
class RelationTypeAdmin(admin.ModelAdmin):
    list_display = ('user', 'label')
    search_fields = ('label',)
    readonly_fields = ('created_at', 'updated_at')


