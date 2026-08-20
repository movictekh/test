from django.db import models

from services.models.property import Property
from services.models.service import ServiceOrder


class Document(models.Model):
    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='svc_documents',
    )
    order = models.ForeignKey(ServiceOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')

    title = models.CharField(max_length=255)
    file_url = models.URLField()
    description = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['order']),
            models.Index(fields=['property']),
        ]

    def __str__(self):
        return f"{self.title}"
