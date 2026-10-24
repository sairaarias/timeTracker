from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import time

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('ADMIN', 'Admin'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='EMPLOYEE')
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    is_approved = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"

class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.now)
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    clock_in_lat = models.FloatField(null=True, blank=True)
    clock_in_lng = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-clock_in']

    @property
    def total_hours(self):
        if self.clock_in and self.clock_out:
            # simple hour calculation
            in_minutes = self.clock_in.hour * 60 + self.clock_in.minute
            out_minutes = self.clock_out.hour * 60 + self.clock_out.minute
            diff = max(0, out_minutes - in_minutes)
            return round(diff / 60, 1)
        return None

class LeaveRequest(models.Model):
    TYPE_CHOICES = (
        ('Sick Leave', 'Sick Leave'),
        ('Vacation Leave', 'Vacation Leave'),
        ('Official Business', 'Official Business'),
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    request_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.request_type} ({self.status})"