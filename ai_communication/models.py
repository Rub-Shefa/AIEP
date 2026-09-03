from django.db import models


class AIQueryLog(models.Model):
    query_text = models.TextField()
    source_interface = models.CharField(max_length=100)
    confidence_score = models.FloatField()
    fallback_triggered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Query Log #{self.id} ({self.confidence_score})"