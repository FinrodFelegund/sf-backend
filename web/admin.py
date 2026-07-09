from django.contrib import admin

from web.models import Entity, Relation, RelationType, Sentence, Website, WebsiteEntity


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'url', 'content_hash', 'created_at', 'updated_at')
    search_fields = ('url', 'user__username')
    list_filter = ('user',)
    readonly_fields = ('created_at', 'updated_at', 'content_hash')


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'website', 'text', 'created_at')
    search_fields = ('text', 'website__url')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'entity_name', 'entity_type', 'created_at')
    search_fields = ('entity_name',)
    list_filter = ('entity_type', 'user')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WebsiteEntity)
class WebsiteEntityAdmin(admin.ModelAdmin):
    list_display = ('website', 'entity', 'count')
    search_fields = ('website__url', 'entity__entity_name')


@admin.register(RelationType)
class RelationTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'label')
    search_fields = ('label',)


@admin.register(Relation)
class RelationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'entity1', 'entity2', 'relation_type')
    search_fields = ('entity1__entity_name', 'entity2__entity_name')
    list_filter = ('user',)