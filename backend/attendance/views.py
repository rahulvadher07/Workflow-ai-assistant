from datetime import datetime, date as date_cls
from calendar import monthrange

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from accounts.models import User
from company.models import is_hod_of, Department
from .models import PunchRecord, AttendanceDay
from .serializers import PunchRecordSerializer, AttendanceDaySerializer
from .services import create_punch, InvalidPunchError


class PunchView(APIView):
    """
    POST only - no body required. Server determines IN/OUT from parity
    and records the punch. No corresponding PATCH/DELETE exists anywhere.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            record = create_punch(request.user)
        except InvalidPunchError as e:
            return Response(
                {"error": {"code": e.code, "message": e.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        punch_count_today = PunchRecord.objects.filter(
            employee=request.user, timestamp__date=timezone.localtime(record.timestamp).date()
        ).count()
        punch_type = "IN" if punch_count_today % 2 == 1 else "OUT"
        return Response(
            {
                "message": f"Punched {punch_type}.",
                "punch": PunchRecordSerializer(record).data,
                "type": punch_type,
            },
            status=status.HTTP_201_CREATED,
        )


class MyAttendanceView(APIView):
    """Own attendance history. Optional ?month=YYYY-MM filter."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = AttendanceDay.objects.filter(employee=request.user)
        qs = _apply_month_filter(qs, request)
        return Response(AttendanceDaySerializer(qs, many=True).data)


class MyAttendanceTodayView(APIView):
    """Today's attendance summary for the logged-in user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        day = AttendanceDay.objects.filter(employee=request.user, date=today).first()
        if not day:
            return Response(
                {
                    "date": str(today), "first_in": None, "last_out": None,
                    "total_minutes": 0, "break_minutes": 0, "overtime_minutes": 0,
                    "is_late": False, "status": "ABSENT", "punch_count": 0, "is_incomplete": False,
                }
            )
        return Response(AttendanceDaySerializer(day).data)


class DepartmentAttendanceView(APIView):
    """
    HOD-only: attendance for employees in the HOD's own department.
    Super Admin: attendance across all employees (optionally filtered by
    department via ?department_id=).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == User.Role.HOD:
            department_ids = Department.objects.filter(hods=user).values_list("id", flat=True)
            legacy_department_ids = Department.objects.filter(hod=user).values_list("id", flat=True)
            qs = AttendanceDay.objects.filter(
                employee__employee_profile__department_id__in=(
                    list(department_ids) + list(legacy_department_ids)
                )
            ).distinct()
        elif user.role == User.Role.SUPER_ADMIN:
            qs = AttendanceDay.objects.all()
            department_id = request.query_params.get("department_id")
            if department_id:
                qs = qs.filter(employee__employee_profile__department_id=department_id)
        else:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have access to department attendance."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = _apply_month_filter(qs, request)
        employee_id = request.query_params.get("employee_id")
        if employee_id:
            qs = qs.filter(employee_id=employee_id)

        return Response(AttendanceDaySerializer(qs.select_related("employee"), many=True).data)


class EmployeeMonthlyAttendanceView(APIView):
    """
    Monthly attendance summary for a single employee - the shape payroll
    will consume later. Employee can fetch their own; HOD can fetch for
    employees in their own department; Super Admin can fetch anyone's.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, employee_id):
        try:
            target = User.objects.select_related("employee_profile__department").get(pk=employee_id)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Employee not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        requester = request.user
        allowed = (
            requester.id == target.id
            or requester.role == User.Role.SUPER_ADMIN
            or (
                requester.role == User.Role.HOD
                and getattr(target, "employee_profile", None)
                and is_hod_of(requester, target.employee_profile.department)
            )
        )
        if not allowed:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You cannot view this employee's attendance."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        month_str = request.query_params.get("month")
        if month_str:
            try:
                parts = month_str.split("-")
                if len(parts) != 2:
                    raise ValueError
                year, month = (int(p) for p in parts)
                if not 1 <= month <= 12:
                    raise ValueError
            except (ValueError, TypeError):
                return Response(
                    {"error": {"code": "VALIDATION_ERROR", "message": "month must be in YYYY-MM format."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            today = timezone.localdate()
            year, month = today.year, today.month

        _, last_day = monthrange(year, month)
        start = date_cls(year, month, 1)
        end = date_cls(year, month, last_day)

        days = AttendanceDay.objects.filter(employee=target, date__gte=start, date__lte=end)

        present_days = days.filter(status=AttendanceDay.Status.PRESENT).count()
        incomplete_days = days.filter(status=AttendanceDay.Status.INCOMPLETE).count()
        late_days = days.filter(is_late=True).count()
        total_minutes = sum(d.total_minutes for d in days)
        total_overtime_minutes = sum(d.overtime_minutes for d in days)

        return Response(
            {
                "employee_id": target.id,
                "year": year,
                "month": month,
                "present_days": present_days,
                "incomplete_days": incomplete_days,
                "late_days": late_days,
                "total_minutes": total_minutes,
                "total_overtime_minutes": total_overtime_minutes,
                "days": AttendanceDaySerializer(days, many=True).data,
            }
        )


def _apply_month_filter(qs, request):
    month_str = request.query_params.get("month")
    if not month_str:
        return qs
    try:
        parts = month_str.split("-")
        if len(parts) != 2:
            raise ValueError
        year, month = (int(p) for p in parts)
        if not 1 <= month <= 12:
            raise ValueError
    except (ValueError, TypeError):
        return qs
    _, last_day = monthrange(year, month)
    start = date_cls(year, month, 1)
    end = date_cls(year, month, last_day)
    return qs.filter(date__gte=start, date__lte=end)
