from django.db import models
from django.utils import timezone

class BaseModel(models.Model):
    created_at = models.DateTimeField(db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if hasattr(self, 'name'):
            return self.name
        return super(BaseModel, self).__str__()
    
    class Meta:
        abstract = True