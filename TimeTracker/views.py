import math
from datetime import time
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import UserProfile, Attendance, LeaveRequest
from django.http import HttpResponse
import csv

# Workplace Geofence Coordinates (Cebu Institute of Technology - University)
WORKPLACE_LAT = 10.2943
WORKPLACE_LNG = 123.8812
ALLOWED_RADIUS_METERS = 100

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
            return redirect('admin_overview')
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        demo_email = request.POST.get('demo_user')
        if demo_email:
            user = User.objects.filter(email=demo_email).first()
            if user:
                login(request, user)
                if hasattr(user, 'profile') and user.profile.role == 'ADMIN':
                    return redirect('admin_overview')
                return redirect('dashboard')

        email = request.POST.get('email')
        password = request.POST.get('password')
        user_obj = User.objects.filter(email=email).first()
        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)
            if user:
                login(request, user)
                if hasattr(user, 'profile') and user.profile.role == 'ADMIN':
                    return redirect('admin_overview')
                return redirect('dashboard')
        error = "Invalid credentials"

    demo_profiles = UserProfile.objects.all()[:3]
    return render(request, 'TimeTracker/login.html', {'error': error, 'demo_profiles': demo_profiles})

def register_view(request):
    if request.method == 'POST':
        role = request.POST.get('role', 'EMPLOYEE')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        department = request.POST.get('department')
        password = request.POST.get('password')
        invite_code = request.POST.get('invite_code', '')

        if role == 'ADMIN' and invite_code != 'ADMIN2026':
            return render(request, 'TimeTracker/register.html', {'error': 'Invalid Admin invite code.'})

        if User.objects.filter(email=email).exists():
            return render(request, 'TimeTracker/register.html', {'error': 'Email already in use.'})

        username = email.split('@')[0]
        user = User.objects.create_user(username=username, email=email, password=password)
        emp_id = f"EMP-{user.id:03d}"
        UserProfile.objects.create(
            user=user,
            role=role,
            full_name=full_name,
            department=department,
            employee_id=emp_id,
            is_approved=True
        )
        login(request, user)
        return redirect('dashboard')

    return render(request, 'TimeTracker/register.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def dashboard(request):
    today = timezone.localdate()
    attendance_today = Attendance.objects.filter(user=request.user, date=today).first()
    recent_attendances = Attendance.objects.filter(user=request.user).exclude(date=today)[:3]

    past_records = Attendance.objects.filter(user=request.user)
    late_count = past_records.filter(is_late=True).count()
    total_hours = sum(r.total_hours or 0 for r in past_records[:7])

    return render(request, 'TimeTracker/dashboard.html', {
        'attendance_today': attendance_today,
        'recent_attendances': recent_attendances,
        'late_count': late_count,
        'total_hours': round(total_hours, 1),
    })

@login_required(login_url='login')
def clock_view(request):
    today = timezone.localdate()
    attendance_today = Attendance.objects.filter(user=request.user, date=today).first()
    message = None
    error = None

    if request.method == 'POST':
        lat = float(request.POST.get('lat', WORKPLACE_LAT))
        lng = float(request.POST.get('lng', WORKPLACE_LNG))
        dist = haversine_distance(lat, lng, WORKPLACE_LAT, WORKPLACE_LNG)

        if dist > ALLOWED_RADIUS_METERS:
            error = f"Outside workplace radius ({round(dist)}m away). Allowed: {ALLOWED_RADIUS_METERS}m."
        else:
            now_time = timezone.localtime().time()
            if not attendance_today:
                is_late = now_time > time(8, 15)
                attendance_today = Attendance.objects.create(
                    user=request.user,
                    date=today,
                    clock_in=now_time,
                    is_late=is_late,
                    clock_in_lat=lat,
                    clock_in_lng=lng
                )
                message = "Clocked in successfully!"
            elif not attendance_today.clock_out:
                attendance_today.clock_out = now_time
                attendance_today.save()
                message = "Clocked out successfully!"

    return render(request, 'TimeTracker/clock.html', {
        'attendance_today': attendance_today,
        'message': message,
        'error': error
    })

@login_required(login_url='login')
def history_view(request):
    records = Attendance.objects.filter(user=request.user)
    on_time_count = records.filter(is_late=False, clock_in__isnull=False).count()
    late_count = records.filter(is_late=True).count()
    return render(request, 'TimeTracker/history.html', {
        'records': records,
        'on_time_count': on_time_count,
        'late_count': late_count
    })

@login_required(login_url='login')
def leave_view(request):
    if request.method == 'POST':
        LeaveRequest.objects.create(
            user=request.user,
            request_type=request.POST.get('request_type'),
            from_date=request.POST.get('from_date'),
            to_date=request.POST.get('to_date'),
            reason=request.POST.get('reason'),
        )
        return redirect('leave')

    requests = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'TimeTracker/leave.html', {'requests': requests})

@login_required(login_url='login')
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        profile.full_name = request.POST.get('full_name')
        profile.department = request.POST.get('department')
        request.user.email = request.POST.get('email')
        profile.save()
        request.user.save()

    return render(request, 'TimeTracker/profile.html', {'profile': profile})

@login_required(login_url='login')
def admin_overview(request):
    today = timezone.localdate()
    staff_profiles = UserProfile.objects.filter(role='EMPLOYEE')

    today_attendances = Attendance.objects.filter(date=today)
    clocked_in_ids = today_attendances.filter(clock_out__isnull=True).values_list('user_id', flat=True)
    completed_ids = today_attendances.filter(clock_out__isnull=False).values_list('user_id', flat=True)

    clocked_in_count = clocked_in_ids.count()
    completed_count = completed_ids.count()
    not_clocked_in_count = staff_profiles.exclude(user_id__in=today_attendances.values_list('user_id', flat=True)).count()

    pending_users_count = UserProfile.objects.filter(is_approved=False).count()
    pending_leaves_count = LeaveRequest.objects.filter(status='Pending').count()

    snapshot = []
    for sp in staff_profiles:
        att = today_attendances.filter(user=sp.user).first()
        status_text = "Not yet"
        if att:
            if att.clock_out:
                status_text = "Completed"
            else:
                status_text = f"{att.clock_in.strftime('%H:%M')}"
        snapshot.append({'profile': sp, 'status': status_text})

    return render(request, 'TimeTracker/admin_overview.html', {
        'clocked_in_count': clocked_in_count,
        'completed_count': completed_count,
        'not_clocked_in_count': not_clocked_in_count,
        'pending_users_count': pending_users_count,
        'pending_leaves_count': pending_leaves_count,
        'snapshot': snapshot,
    })

@login_required(login_url='login')
def admin_logs(request):
    today = timezone.localdate()
    attendances = Attendance.objects.filter(date=today)
    all_profiles = UserProfile.objects.all()

    logs = []
    for prof in all_profiles:
        att = attendances.filter(user=prof.user).first()
        logs.append({
            'profile': prof,
            'clock_in': att.clock_in if att else None,
            'clock_out': att.clock_out if att else None,
            'att_id': att.id if att else None,
        })

    return render(request, 'TimeTracker/admin_logs.html', {'logs': logs, 'today': today})

@login_required(login_url='login')
def admin_leave_approval(request):
    if request.method == 'POST':
        leave_id = request.POST.get('leave_id')
        action = request.POST.get('action')
        leave = LeaveRequest.objects.filter(id=leave_id).first()
        if leave:
            leave.status = 'Approved' if action == 'approve' else 'Rejected'
            leave.save()
            return redirect('admin_leave')

    pending_leaves = LeaveRequest.objects.filter(status='Pending').order_by('-created_at')
    return render(request, 'TimeTracker/admin_leave.html', {'pending_leaves': pending_leaves})

@login_required(login_url='login')
def admin_users(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        prof = UserProfile.objects.filter(id=user_id).first()
        if prof:
            if action == 'verify':
                prof.is_approved = True
                prof.save()
            elif action == 'decline':
                prof.user.delete()
            return redirect('admin_users')

    unapproved_users = UserProfile.objects.filter(is_approved=False)
    all_staff = UserProfile.objects.all()
    return render(request, 'TimeTracker/admin_users.html', {
        'unapproved_users': unapproved_users,
        'all_staff': all_staff
    })

@login_required(login_url='login')
def admin_reports(request):
    # Retrieve all unique departments registered by users
    departments = (
        UserProfile.objects.exclude(department__isnull=True)
        .exclude(department__exact='')
        .values_list('department', flat=True)
        .distinct()
        .order_by('department')
    )

    selected_department = request.GET.get('department', '').strip()

    # Query attendance records with related user and profile data
    records = Attendance.objects.select_related('user__profile').all().order_by('-date')

    # Apply department filter if selected
    if selected_department and selected_department != 'ALL':
        records = records.filter(user__profile__department__iexact=selected_department)

    # Handle CSV Export
    if request.method == 'POST':
        response = HttpResponse(content_type='text/csv')
        filename = f"attendance_report_{selected_department or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Name', 'Department', 'Clock In', 'Clock Out', 'Late'])
        for a in records:
            name = getattr(getattr(a.user, 'profile', None), 'full_name', a.user.username)
            dept = getattr(getattr(a.user, 'profile', None), 'department', '-')
            writer.writerow([a.date, name, dept, a.clock_in, a.clock_out, a.is_late])
        return response

    return render(request, 'TimeTracker/admin_reports.html', {
        'departments': departments,
        'selected_department': selected_department,
        'records': records,
    })