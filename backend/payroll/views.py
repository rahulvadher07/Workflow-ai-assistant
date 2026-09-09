from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsSuperAdmin, IsHOD
from .models import EmployeeSalary, PayrollPeriod, Payslip
from .serializers import EmployeeSalarySerializer, PayrollPeriodSerializer, PayslipSerializer
from .services import generate_draft_payroll, approve_payslip, send_payslip_email, PayrollError
from .pdf import generate_payslip_pdf


def _is_authorized_for_employee(actor, employee):
    if actor.role == User.Role.SUPER_ADMIN:
        return True
    if actor.role == User.Role.HOD:
        profile = getattr(employee, "employee_profile", None)
        return profile is not None and __import__("company.models", fromlist=["is_hod_of"]).is_hod_of(actor, profile.department)
    return False


class EmployeeSalaryView(APIView):
    """
    GET: view an employee's salary config (self, own-dept HOD, or admin).
    PUT: set/update salary config (Admin or the employee's own-dept HOD only).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, employee_id):
        employee = User.objects.filter(pk=employee_id).select_related("employee_profile__department").first()
        if employee is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "Employee not found."}}, status=404)

        if request.user.id != employee.id and not _is_authorized_for_employee(request.user, employee):
            return Response({"error": {"code": "FORBIDDEN", "message": "Not authorized."}}, status=403)

        salary = EmployeeSalary.objects.filter(employee=employee).first()
        if salary is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "No salary configured."}}, status=404)
        return Response(EmployeeSalarySerializer(salary).data)

    def put(self, request, employee_id):
        employee = User.objects.filter(pk=employee_id).select_related("employee_profile__department").first()
        if employee is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "Employee not found."}}, status=404)

        if not _is_authorized_for_employee(request.user, employee):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only Super Admin or the employee's HOD can set salary."}},
                status=403,
            )

        salary = EmployeeSalary.objects.filter(employee=employee).first()
        is_create = salary is None

        serializer = EmployeeSalarySerializer(salary, data=request.data, partial=not is_create)
        serializer.is_valid(raise_exception=True)

        if is_create and "basic_monthly_salary" not in serializer.validated_data:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "basic_monthly_salary is required to create a new salary configuration."}},
                status=400,
            )

        serializer.save(employee=employee, updated_by=request.user)
        return Response(EmployeeSalarySerializer(serializer.instance).data)


class PayrollGenerateView(APIView):
    """POST: generate/refresh draft payroll for a given year+month. Admin only (month-end trigger)."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        year = request.data.get("year")
        month = request.data.get("month")
        if not year or not month:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "year and month are required."}}, status=400
            )
        try:
            year = int(year)
            month = int(month)
        except (TypeError, ValueError):
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "year and month must be integers."}}, status=400
            )
        if not 1 <= month <= 12 or year < 1:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "year must be positive and month must be between 1 and 12."}}, status=400
            )

        result = generate_draft_payroll(year, month)
        return Response(
            {
                "period": PayrollPeriodSerializer(result["period"]).data,
                "payslips_generated": result["payslips_generated"],
                "already_approved_skipped": result["already_approved_skipped"],
            }
        )


class PayslipListView(APIView):
    """
    GET: Employee -> own payslips only.
         HOD -> own department's payslips.
         Super Admin -> all, optionally filtered by employee_id/department via query params.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.Role.SUPER_ADMIN:
            qs = Payslip.objects.all()
        elif user.role == User.Role.HOD:
            from company.models import Department
            department_ids = list(Department.objects.filter(hods=user).values_list("id", flat=True))
            department_ids.extend(Department.objects.filter(hod=user).values_list("id", flat=True))
            qs = Payslip.objects.filter(employee__employee_profile__department_id__in=department_ids)
        else:
            qs = Payslip.objects.filter(employee=user)

        year = request.query_params.get("year")
        month = request.query_params.get("month")
        if year:
            qs = qs.filter(period__year=year)
        if month:
            qs = qs.filter(period__month=month)

        # Employees only ever see approved payslips - a draft is not
        # "their payroll history" yet.
        if user.role == User.Role.EMPLOYEE:
            qs = qs.filter(status=Payslip.Status.HOD_APPROVED)

        return Response(PayslipSerializer(qs.select_related("employee", "period"), many=True, context={"request": request}).data)


class PayslipDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        payslip = Payslip.objects.filter(pk=pk).select_related("employee__employee_profile__department", "period").first()
        if payslip is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "Payslip not found."}}, status=404)

        user = request.user
        authorized = (
            user.id == payslip.employee_id
            or _is_authorized_for_employee(user, payslip.employee)
        )
        if not authorized:
            return Response({"error": {"code": "FORBIDDEN", "message": "Not authorized."}}, status=403)

        if user.role == User.Role.EMPLOYEE and payslip.status != Payslip.Status.HOD_APPROVED:
            return Response({"error": {"code": "FORBIDDEN", "message": "This payslip is not yet approved."}}, status=403)

        return Response(PayslipSerializer(payslip, context={"request": request}).data)


class PayslipApproveView(APIView):
    """POST: HOD approves one employee's payslip. Generates PDF + notifies employee."""

    permission_classes = [permissions.IsAuthenticated, IsHOD]

    def post(self, request, pk):
        payslip = Payslip.objects.filter(pk=pk).select_related("employee__employee_profile__department", "period").first()
        if payslip is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "Payslip not found."}}, status=404)

        try:
            updated = approve_payslip(payslip, request.user)
        except PayrollError as e:
            http_status = 403 if e.code == "FORBIDDEN" else 409 if e.code == "INVALID_PAYROLL_STATE" else 400
            return Response({"error": {"code": e.code, "message": e.message}}, status=http_status)

        generate_payslip_pdf(updated)
        try:
            send_payslip_email(updated)
        except Exception:
            # Email delivery failure should not undo the approval that
            # already succeeded - the payslip is still approved and
            # visible in-app; email is a best-effort delivery channel.
            pass
        return Response(PayslipSerializer(updated, context={"request": request}).data)


class PayslipDownloadView(APIView):
    """GET: redirect/serve the payslip PDF file, same authorization as detail view."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        payslip = Payslip.objects.filter(pk=pk).select_related("employee__employee_profile__department").first()
        if payslip is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "Payslip not found."}}, status=404)

        user = request.user
        authorized = user.id == payslip.employee_id or _is_authorized_for_employee(user, payslip.employee)
        if not authorized:
            return Response({"error": {"code": "FORBIDDEN", "message": "Not authorized."}}, status=403)

        if user.role == User.Role.EMPLOYEE and payslip.status != Payslip.Status.HOD_APPROVED:
            return Response({"error": {"code": "FORBIDDEN", "message": "This payslip is not yet approved."}}, status=403)

        if not payslip.pdf_file:
            return Response({"error": {"code": "NOT_FOUND", "message": "PDF not generated yet."}}, status=404)

        from django.http import FileResponse
        return FileResponse(payslip.pdf_file.open("rb"), as_attachment=True, filename=payslip.pdf_file.name.split("/")[-1])
