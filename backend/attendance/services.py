"""
Attendance calculation logic. Backend is the sole source of truth for
working hours, breaks, late status and overtime - nothing here is
decided by the frontend.
"""

from datetime import datetime, timedelta, time
from django.db import transaction
from django.utils import timezone

from company.models import Company
from .models import PunchRecord, AttendanceDay


class InvalidPunchError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def create_punch(employee, when=None):
    """Create one raw attendance punch; the backend derives IN/OUT by parity.

    Action contract: reject future timestamps, reject accidental double punches
    inside the short duplicate window, serialize one employee's punches, persist
    the raw punch, and recalculate the authoritative AttendanceDay. The AI must
    never write an attendance status/time directly.
    """
    """
    Records a punch for `employee` at `when` (defaults to now). Type
    (IN/OUT) is never stored - it is derived from parity when reading.

    Validates:
    - no duplicate punch within a short window (accidental double-click)
    - punch is not in the future
    """
    when = when or timezone.now()

    if when > timezone.now() + timedelta(minutes=1):
        raise InvalidPunchError("INVALID_PUNCH_SEQUENCE", "Cannot punch for a future time.")

    with transaction.atomic():
        # Serialize punches for one employee. Without a stable row lock, two
        # concurrent first punches can both observe the same parity and both
        # be recorded.
        from accounts.models import User
        employee = User.objects.select_for_update().get(pk=employee.pk)

        today = timezone.localtime(when).date()
        local_tz = timezone.get_current_timezone()
        day_start = timezone.make_aware(datetime.combine(today, time.min), local_tz)
        day_end = timezone.make_aware(datetime.combine(today, time.max), local_tz)

        existing_today = list(
            PunchRecord.objects.select_for_update()
            .filter(employee=employee, timestamp__gte=day_start, timestamp__lte=day_end)
            .order_by("timestamp")
        )

        if existing_today:
            last_punch = existing_today[-1]
            if (when - last_punch.timestamp) < timedelta(seconds=30):
                raise InvalidPunchError(
                    "DUPLICATE_REQUEST", "Duplicate punch request - please wait before punching again."
                )

        record = PunchRecord.objects.create(employee=employee, timestamp=when)
        recalculate_day(employee, today)
        return record


def _pair_punches(punches):
    """Pairs sequential punches: (1st,2nd) IN/OUT, (3rd,4th) IN/OUT, ...
    Returns (complete_pairs, unmatched_final_in_or_none)."""
    pairs = []
    i = 0
    while i + 1 < len(punches):
        pairs.append((punches[i], punches[i + 1]))
        i += 2
    unmatched = punches[i] if i < len(punches) else None
    return pairs, unmatched


def recalculate_day(employee, date):
    """
    Recomputes AttendanceDay from raw PunchRecord rows for that employee/date.
    Called after every punch. This is the single place calculation logic lives.
    """
    local_tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.combine(date, time.min), local_tz)
    day_end = timezone.make_aware(datetime.combine(date, time.max), local_tz)

    punches = list(
        PunchRecord.objects.filter(
            employee=employee, timestamp__gte=day_start, timestamp__lte=day_end
        ).order_by("timestamp")
    )

    company = Company.get_solo()

    attendance_day, _ = AttendanceDay.objects.get_or_create(employee=employee, date=date)

    if not punches:
        attendance_day.first_in = None
        attendance_day.last_out = None
        attendance_day.total_minutes = 0
        attendance_day.break_minutes = 0
        attendance_day.overtime_minutes = 0
        attendance_day.is_late = False
        attendance_day.status = AttendanceDay.Status.ABSENT
        attendance_day.punch_count = 0
        attendance_day.save()
        return attendance_day

    pairs, unmatched = _pair_punches(punches)

    worked_minutes = 0
    for in_punch, out_punch in pairs:
        delta = out_punch.timestamp - in_punch.timestamp
        worked_minutes += max(0, int(delta.total_seconds() // 60))

    break_minutes = 0
    # Auto-deduct configured break ONLY when there is exactly one
    # completed pair for the day (single IN/OUT). Multiple pairs already
    # represent the break as the gap between OUT and the next IN - do not
    # double-deduct.
    if len(pairs) == 1 and unmatched is None:
        break_minutes = company.standard_break_minutes
        worked_minutes = max(0, worked_minutes - break_minutes)

    first_in = punches[0].timestamp
    last_out = pairs[-1][1].timestamp if pairs else None

    is_late = False
    shift_start = company.shift_start_time
    local_first_in = timezone.localtime(first_in)
    if local_first_in.time() > shift_start:
        is_late = True

    overtime_minutes = 0
    if unmatched is None:
        overtime_minutes = max(0, worked_minutes - company.standard_shift_minutes)

    if unmatched is not None:
        status = AttendanceDay.Status.INCOMPLETE
    else:
        status = AttendanceDay.Status.PRESENT

    attendance_day.first_in = first_in
    attendance_day.last_out = last_out
    attendance_day.total_minutes = worked_minutes
    attendance_day.break_minutes = break_minutes
    attendance_day.overtime_minutes = overtime_minutes
    attendance_day.is_late = is_late
    attendance_day.status = status
    attendance_day.punch_count = len(punches)
    attendance_day.save()
    return attendance_day
