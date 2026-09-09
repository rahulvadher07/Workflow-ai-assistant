from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from .models import LeaveRequest
from .services import LeaveError, approve_leave_request, reject_leave_request


def _serialize(request):
    return {
        "id": request.id,
        "employee_id": request.employee_id,
        "employee_name": request.employee.get_full_name() or request.employee.username,
        "employee_role": request.employee.role,
        "department": request.employee.employee_profile.department.name,
        "leave_type": request.leave_type.name,
        "from_date": request.from_date,
        "to_date": request.to_date,
        "days": request.days,
        "reason": request.reason,
        "status": request.status,
        "approved_by": request.approved_by.get_full_name() if request.approved_by else None,
        "created_at": request.created_at,
        "decided_at": request.decided_at,
    }


class HODLeaveApprovalListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.SUPER_ADMIN:
            return Response({"error": {"code": "FORBIDDEN", "message": "Only Super Admin can view HOD leave requests."}}, status=status.HTTP_403_FORBIDDEN)
        qs = (LeaveRequest.objects
              .filter(employee__role=User.Role.HOD)
              .select_related("employee__employee_profile__department", "leave_type", "approved_by")
              .order_by("-created_at"))
        return Response([_serialize(item) for item in qs])


class HODLeaveApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != User.Role.SUPER_ADMIN:
            return Response({"error": {"code": "FORBIDDEN", "message": "Only Super Admin can approve HOD leave."}}, status=status.HTTP_403_FORBIDDEN)
        leave_request = LeaveRequest.objects.filter(pk=pk, employee__role=User.Role.HOD).first()
        if not leave_request:
            return Response({"error": {"code": "NOT_FOUND", "message": "HOD leave request not found."}}, status=status.HTTP_404_NOT_FOUND)
        try:
            return Response(_serialize(approve_leave_request(leave_request, request.user)))
        except LeaveError as exc:
            return Response({"error": {"code": exc.code, "message": exc.message}}, status=status.HTTP_400_BAD_REQUEST)


class HODLeaveRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != User.Role.SUPER_ADMIN:
            return Response({"error": {"code": "FORBIDDEN", "message": "Only Super Admin can reject HOD leave."}}, status=status.HTTP_403_FORBIDDEN)
        leave_request = LeaveRequest.objects.filter(pk=pk, employee__role=User.Role.HOD).first()
        if not leave_request:
            return Response({"error": {"code": "NOT_FOUND", "message": "HOD leave request not found."}}, status=status.HTTP_404_NOT_FOUND)
        try:
            return Response(_serialize(reject_leave_request(leave_request, request.user)))
        except LeaveError as exc:
            return Response({"error": {"code": exc.code, "message": exc.message}}, status=status.HTTP_400_BAD_REQUEST)
