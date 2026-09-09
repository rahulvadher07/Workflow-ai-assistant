from rest_framework.permissions import BasePermission
from core.permissions_base import IsSuperAdmin, IsHOD, IsEmployee, IsSameDepartmentHOD

__all__ = ["IsSuperAdmin", "IsHOD", "IsEmployee", "IsSameDepartmentHOD"]
