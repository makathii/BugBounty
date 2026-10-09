from django.conf import settings
from django.db import models

from .program import Program


class ProgramFavorite(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='favorites')
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_programs'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['program', 'researcher']
        ordering = ['-created_at']
        indexes = [models.Index(fields=['researcher', 'created_at'])]

    def __str__(self):
        return f"{self.researcher.username} ★ {self.program.name}"
