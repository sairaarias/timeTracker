from django.contrib import admin
from .models import UserProfile, Attendance, LeaveRequest

admin.site.register(UserProfile)
admin.site.register(Attendance)
admin.site.register(LeaveRequest)