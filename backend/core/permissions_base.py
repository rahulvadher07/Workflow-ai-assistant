from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.SUPER_ADMIN
        )


class IsHOD(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.HOD
        )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.EMPLOYEE
        )


class IsSameDepartmentHOD(BasePermission):
    """
    Object-level check: the requesting user must be the HOD of the
    department that the target object's employee belongs to.

    Expects the view to implement `get_target_department(obj)` OR the
    object to have a resolvable `.employee.department` / `.department`
    attribute. Views using this should override has_object_permission
    logic implicitly by ensuring obj exposes a department.
    """

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role != request.user.Role.HOD:
            return False

        department = None
        if hasattr(obj, "department"):
            department = obj.department
        elif hasattr(obj, "employee"):
            target_user = obj.employee
            profile = getattr(target_user, "employee_profile", None)
            department = profile.department if profile else None
        elif hasattr(obj, "user"):
            profile = getattr(obj.user, "employee_profile", None)
            department = profile.department if profile else None

        if department is None:
            return False

        from company.models import is_hod_of
        return is_hod_of(request.user, department)
