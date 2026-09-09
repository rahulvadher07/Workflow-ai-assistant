from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsHOD
from company.models import Department, is_hod_of
from .models import Team, TeamMembership
from .serializers import TeamSerializer, TeamCreateSerializer, AddMemberSerializer


class TeamListCreateView(APIView):
    """
    GET: Employee -> only teams they're a member of.
         HOD -> teams in their own department.
         Super Admin -> all teams.
    POST: HOD only, creates a team in their own department.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.Role.HOD:
            qs = Team.objects.filter(department__in=Department.objects.filter(hods=user) | Department.objects.filter(hod=user))
        elif user.role == User.Role.SUPER_ADMIN:
            qs = Team.objects.all()
        else:
            qs = Team.objects.filter(memberships__employee=user)
        return Response(TeamSerializer(qs.distinct(), many=True).data)

    def post(self, request):
        if request.user.role != User.Role.HOD:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only an HOD can create a team."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        department = (Department.objects.filter(hods=request.user).first() or Department.objects.filter(hod=request.user).first())
        if department is None:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You are not assigned as HOD of any department."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.save(department=department, created_by=request.user)
        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        team = _get_team_or_none(pk)
        if team is None:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Team not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not _can_view_team(request.user, team):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have access to this team."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(TeamSerializer(team).data)


class TeamMemberView(APIView):
    """
    POST: HOD adds an employee to their own department's team.
    DELETE: HOD removes an employee from their own department's team.
    """

    permission_classes = [permissions.IsAuthenticated, IsHOD]

    def post(self, request, pk):
        team = _get_team_or_none(pk)
        if team is None or not is_hod_of(request.user, team.department):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You cannot manage this team."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.validated_data["employee_id"]
        is_lead = serializer.validated_data.get("is_lead", False)

        # Employee must belong to the same department as the team.
        profile = getattr(employee, "employee_profile", None)
        if profile is None or profile.department_id != team.department_id:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Employee is not in this team's department."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership, created = TeamMembership.objects.get_or_create(
            team=team, employee=employee, defaults={"is_lead": is_lead}
        )
        if not created:
            return Response(
                {"error": {"code": "DUPLICATE_REQUEST", "message": "Employee is already a member of this team."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, employee_id):
        team = _get_team_or_none(pk)
        if team is None or not is_hod_of(request.user, team.department):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You cannot manage this team."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        deleted, _ = TeamMembership.objects.filter(team=team, employee_id=employee_id).delete()
        if not deleted:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "This employee is not a member of the team."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TeamSerializer(team).data)


def _get_team_or_none(pk):
    return Team.objects.filter(pk=pk).select_related("department").first()


def _can_view_team(user, team):
    if user.role == User.Role.SUPER_ADMIN:
        return True
    if user.role == User.Role.HOD:
        return __import__("company.models", fromlist=["is_hod_of"]).is_hod_of(user, team.department)
    return TeamMembership.objects.filter(team=team, employee=user).exists()
