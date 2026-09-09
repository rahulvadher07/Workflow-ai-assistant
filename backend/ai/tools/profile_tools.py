"""
Every tool function takes `user` (the real authenticated Django user,
bound by the orchestrator - never taken from model-supplied arguments)
as its first argument, and returns a plain JSON-serializable dict.
Tools never accept an employee_id/user_id argument from the model for
scope - if a target-employee argument is needed, it is validated
against Django permissions same as a normal DRF view would.
"""

from django.forms.models import model_to_dict


def get_my_profile(user):
    profile = getattr(user, "employee_profile", None)
    return {
        "name": user.get_full_name() or user.username,
        "role": user.role,
        "department": profile.department.name if profile else None,
        "employee_code": profile.employee_code if profile else None,
    }
