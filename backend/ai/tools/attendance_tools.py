from datetime import date as date_cls
from calendar import monthrange

from attendance.models import AttendanceDay
from django.utils import timezone


def get_my_attendance(user, date_str=None):
    """
    date_str: 'YYYY-MM-DD', defaults to today. Reads the already-computed
    AttendanceDay - never recalculates here (backend calc remains the
    single source of truth per architecture.md).
    """
    if date_str:
        try:
            parts = date_str.split("-")
            if len(parts) != 3:
                raise ValueError
            year, month, day = (int(p) for p in parts)
            target_date = date_cls(year, month, day)
        except (ValueError, TypeError):
            return {"error": "Invalid date format, expected YYYY-MM-DD."}
    else:
        target_date = timezone.localdate()

    day = AttendanceDay.objects.filter(employee=user, date=target_date).first()
    if not day:
        return {"date": str(target_date), "status": "ABSENT", "message": "No punches recorded for this date."}

    return {
        "date": str(day.date),
        "first_in": day.first_in.isoformat() if day.first_in else None,
        "last_out": day.last_out.isoformat() if day.last_out else None,
        "total_minutes": day.total_minutes,
        "total_hours": round(day.total_minutes / 60, 2),
        "break_minutes": day.break_minutes,
        "overtime_minutes": day.overtime_minutes,
        "is_late": day.is_late,
        "status": day.status,
    }


def get_my_attendance_summary(user, month_str=None):
    """month_str: 'YYYY-MM', defaults to current month."""
    if month_str:
        try:
            parts = month_str.split("-")
            if len(parts) != 2:
                raise ValueError
            year, month = (int(p) for p in parts)
            if not 1 <= month <= 12:
                raise ValueError
        except (ValueError, TypeError):
            return {"error": "Invalid month format, expected YYYY-MM."}
    else:
        today = timezone.localdate()
        year, month = today.year, today.month

    _, last_day = monthrange(year, month)
    start = date_cls(year, month, 1)
    end = date_cls(year, month, last_day)

    days = AttendanceDay.objects.filter(employee=user, date__gte=start, date__lte=end)
    present_days = days.filter(status=AttendanceDay.Status.PRESENT).count()
    late_days = days.filter(is_late=True).count()
    total_minutes = sum(d.total_minutes for d in days)
    total_overtime_minutes = sum(d.overtime_minutes for d in days)

    return {
        "year": year,
        "month": month,
        "present_days": present_days,
        "late_days": late_days,
        "total_hours": round(total_minutes / 60, 2),
        "total_overtime_hours": round(total_overtime_minutes / 60, 2),
    }
