# models.py - Add these fields to your existing ScanHistory model

from django.db import models
from django.utils import timezone

class Criminal(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='criminals/', null=True, blank=True)
    date_added = models.DateTimeField(default=timezone.now, null=True, blank=True)
    
    def __str__(self):
        return self.name

class ScanHistory(models.Model):
    DETECTION_TYPES = [
        ('upload', 'File Upload'),
        ('real_time_camera', 'Real-time Camera'),
        ('single_capture', 'Single Capture'),
    ]
    
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='scans/', null=True, blank=True)
    date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    confidence = models.FloatField(default=0.0, help_text="Detection confidence percentage", null=True, blank=True)
    detection_type = models.CharField(max_length=20, choices=DETECTION_TYPES, default='upload', null=True, blank=True)
    is_criminal = models.BooleanField(default=False, null=True, blank=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Scan Histories"
    
    def __str__(self):
        return f"{self.name} - {self.date.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        # Auto-set is_criminal based on name
        self.is_criminal = self.name not in ['Unknown', 'No face']
        super().save(*args, **kwargs)

# Migration command to run:
# python manage.py makemigrations
# python manage.py migrate