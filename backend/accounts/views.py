from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, EmployeeProfile
from .permissions import IsHOD
from core.permissions_base import IsSuperAdmin
from company.models import Department
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PendingRegistrationSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    CreateHODSerializer, AdminUserUpdateSerializer, ProfileUpdateSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Public employee self-registration. Always creates PENDING/EMPLOYEE."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        department = user.employee_profile.department
        from company.models import department_hod_queryset
        from notifications.services import notify
        from notifications.models import Notification
        for hod in department_hod_queryset(department):
            notify(
                recipient=hod,
                verb=Notification.Verb.REGISTRATION_SUBMITTED,
                title="New registration awaiting approval",
                message=f"{user.get_full_name() or user.username} has requested to join {department.name}.",
                related_object=user,
            )

        return Response(
            {
                "message": "Registration submitted. Your account is pending HOD approval.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    """Blacklists the provided refresh token."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "refresh token is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Invalid or already-invalidated token."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Logged out successfully."}, status=status.HTTP_205_RESET_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password changed successfully."})


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class EmployeeListView(APIView):
    """
    Admin: all active employees. HOD: only own-department employees.
    Matches the same department-scoping pattern used throughout (e.g.
    PendingRegistrationListView, attendance department view).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = User.objects.filter(status=User.Status.ACTIVE).exclude(
            role=User.Role.SUPER_ADMIN
        ).select_related("employee_profile__department")

        if user.role == User.Role.SUPER_ADMIN:
            qs = qs.filter(role=User.Role.EMPLOYEE).order_by("first_name", "username")
        elif user.role == User.Role.HOD:
            department_ids = Department.objects.filter(hods=user).values_list("id", flat=True)
            legacy_ids = Department.objects.filter(hod=user).values_list("id", flat=True)
            qs = qs.filter(
                employee_profile__department_id__in=(list(department_ids) + list(legacy_ids)),
                role=User.Role.EMPLOYEE,
            ).order_by("first_name", "username")
        else:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have access to the employee list."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(UserSerializer(qs.filter(role=User.Role.EMPLOYEE), many=True).data)


class HODListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        qs = User.objects.filter(role=User.Role.HOD, status=User.Status.ACTIVE).select_related("employee_profile__department").order_by("first_name", "username")
        return Response(UserSerializer(qs, many=True).data)


class HODCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = CreateHODSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(UserSerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


class AdminUserUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def patch(self, request, pk):
        target = User.objects.filter(pk=pk).exclude(role=User.Role.SUPER_ADMIN).select_related("employee_profile").first()
        if target is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "User not found."}}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserUpdateSerializer(target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(UserSerializer(serializer.save()).data)


class PendingRegistrationListView(generics.ListAPIView):
    """
    HOD-only: list PENDING employees whose department is this HOD's
    department. Scoped strictly - an HOD never sees other departments'
    pending registrations.
    """

    serializer_class = PendingRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated, IsHOD]

    def get_queryset(self):
        hod = self.request.user
        from company.models import Department
        department_ids = list(Department.objects.filter(hods=hod).values_list("id", flat=True))
        department_ids.extend(Department.objects.filter(hod=hod).values_list("id", flat=True))
        return (
            User.objects.filter(
                status=User.Status.PENDING,
                employee_profile__department_id__in=department_ids,
            )
            .select_related("employee_profile", "employee_profile__department")
            .order_by("date_joined")
        )


class ApproveRegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHOD]

    def post(self, request, pk):
        return _decide_registration(request, pk, approve=True)


class RejectRegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHOD]

    def post(self, request, pk):
        return _decide_registration(request, pk, approve=False)


def _decide_registration(request, pk, approve):
    hod = request.user
    try:
        with transaction.atomic():
            # select_for_update() cannot be combined with select_related()
            # across a nullable relation (EmployeeProfile is an optional
            # reverse OneToOne) - Postgres rejects "FOR UPDATE" across an
            # outer join. Lock the User row alone, then fetch the profile
            # separately.
            target = User.objects.select_for_update().get(pk=pk)
            profile = EmployeeProfile.objects.select_related("department").filter(user=target).first()
            if profile is None:
                return Response(
                    {"error": {"code": "FORBIDDEN", "message": "This registration is not in your department."}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            from company.models import is_hod_of
            if not is_hod_of(hod, profile.department):
                return Response(
                    {"error": {"code": "FORBIDDEN", "message": "This registration is not in your department."}},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if target.status != User.Status.PENDING:
                return Response(
                    {
                        "error": {
                            "code": "REGISTRATION_ALREADY_DECIDED",
                            "message": f"This registration was already {target.status.lower()}.",
                        }
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            target.status = User.Status.ACTIVE if approve else User.Status.REJECTED
            target.save(update_fields=["status"])
    except User.DoesNotExist:
        return Response(
            {"error": {"code": "NOT_FOUND", "message": "Registration not found."}},
            status=status.HTTP_404_NOT_FOUND,
        )

    from notifications.services import notify
    from notifications.models import Notification
    notify(
        recipient=target,
        verb=Notification.Verb.REGISTRATION_APPROVED if approve else Notification.Verb.REGISTRATION_REJECTED,
        title="Registration approved" if approve else "Registration rejected",
        message="You can now log in." if approve else "Your registration was not approved.",
        related_object=target,
    )

    return Response(
        {
            "message": f"Registration {'approved' if approve else 'rejected'}.",
            "user": UserSerializer(target).data,
        }
    )
