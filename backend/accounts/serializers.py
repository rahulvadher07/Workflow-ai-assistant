from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction

from company.models import Department
from .models import User, EmployeeProfile


class RegisterSerializer(serializers.Serializer):
    """
    Employee self-registration. Creates User(status=PENDING, role=EMPLOYEE)
    + EmployeeProfile. Never allows role or status to be set by the caller.
    """

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="department"
    )
    employee_code = serializers.CharField(max_length=30)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_employee_code(self, value):
        if EmployeeProfile.objects.filter(employee_code=value).exists():
            raise serializers.ValidationError("This employee code is already in use.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        department = validated_data.pop("department")
        password = validated_data.pop("password")
        phone = validated_data.pop("phone", "")
        employee_code = validated_data.pop("employee_code")

        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data.get("last_name", ""),
            role=User.Role.EMPLOYEE,
            status=User.Status.PENDING,
        )
        user.set_password(password)
        user.save()

        EmployeeProfile.objects.create(
            user=user,
            department=department,
            employee_code=employee_code,
            phone=phone,
        )
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    department_id = serializers.IntegerField(required=False, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, write_only=True)
    employee_code = serializers.CharField(required=False, write_only=True)
    password = serializers.CharField(required=False, write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "department_id", "phone", "employee_code", "password"]
        read_only_fields = ["username"]

    def validate_department_id(self, value):
        from company.models import Department
        if not Department.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Department not found.")
        return value

    def validate_employee_code(self, value):
        qs = EmployeeProfile.objects.filter(employee_code=value).exclude(user=self.instance)
        if qs.exists():
            raise serializers.ValidationError("This employee code is already in use.")
        return value

    def update(self, instance, validated_data):
        department_id = validated_data.pop("department_id", None)
        phone = validated_data.pop("phone", None)
        employee_code = validated_data.pop("employee_code", None)
        password = validated_data.pop("password", None)
        user_changed = []
        for key, value in validated_data.items():
            if getattr(instance, key) != value:
                setattr(instance, key, value)
                user_changed.append(key)
        if password:
            instance.set_password(password)
            user_changed.append("password")
        if user_changed:
            instance.save(update_fields=user_changed)
        profile = getattr(instance, "employee_profile", None)
        if profile:
            changed = []
            if phone is not None and profile.phone != phone:
                profile.phone = phone; changed.append("phone")
            if employee_code is not None and profile.employee_code != employee_code:
                profile.employee_code = employee_code; changed.append("employee_code")
            if department_id is not None and profile.department_id != department_id:
                profile.department_id = department_id; changed.append("department")
            if changed:
                profile.save(update_fields=changed)
                if instance.role == User.Role.HOD and department_id is not None:
                    from company.models import Department, DepartmentHOD
                    DepartmentHOD.objects.filter(hod=instance).exclude(department_id=department_id).delete()
                    DepartmentHOD.objects.get_or_create(department_id=department_id, hod=instance)
                    Department.objects.filter(hod=instance).exclude(pk=department_id).update(hod=None)
                    if not Department.objects.filter(pk=department_id, hod=instance).exists():
                        Department.objects.filter(pk=department_id, hod__isnull=True).update(hod=instance)
        return instance


class CreateHODSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    department_id = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), source="department")
    employee_code = serializers.CharField(max_length=30)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_employee_code(self, value):
        if EmployeeProfile.objects.filter(employee_code=value).exists():
            raise serializers.ValidationError("This employee code is already in use.")
        return value

    def validate_password(self, value):
        validate_password(value); return value

    @transaction.atomic
    def create(self, validated_data):
        from company.models import DepartmentHOD, Department
        department = validated_data.pop("department")
        password = validated_data.pop("password")
        phone = validated_data.pop("phone", "")
        employee_code = validated_data.pop("employee_code")
        user = User(
            username=validated_data["username"], email=validated_data["email"],
            first_name=validated_data["first_name"], last_name=validated_data.get("last_name", ""),
            role=User.Role.HOD, status=User.Status.ACTIVE,
        )
        user.set_password(password); user.save()
        EmployeeProfile.objects.create(user=user, department=department, employee_code=employee_code, phone=phone)
        DepartmentHOD.objects.get_or_create(department=department, hod=user)
        if department.hod_id is None:
            department.hod = user; department.save(update_fields=["hod"])
        return user


class UserSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    department_id = serializers.SerializerMethodField()
    employee_code = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "status", "department", "department_id", "employee_code", "phone",
        ]
        read_only_fields = fields

    def get_department(self, obj):
        profile = getattr(obj, "employee_profile", None)
        return profile.department.name if profile else None

    def get_department_id(self, obj):
        profile = getattr(obj, "employee_profile", None)
        return profile.department_id if profile else None

    def get_employee_code(self, obj):
        profile = getattr(obj, "employee_profile", None)
        return profile.employee_code if profile else None

    def get_phone(self, obj):
        profile = getattr(obj, "employee_profile", None)
        return profile.phone if profile else None


class PendingRegistrationSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="employee_profile.department.name", read_only=True)
    employee_code = serializers.CharField(source="employee_profile.employee_code", read_only=True)
    phone = serializers.CharField(source="employee_profile.phone", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "status", "department", "employee_code", "phone", "date_joined",
        ]
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Blocks login for PENDING/REJECTED/SUSPENDED accounts with a clear
    error rather than a generic auth failure.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        if self.user.status != User.Status.ACTIVE:
            if self.user.status == User.Status.PENDING:
                raise serializers.ValidationError(
                    {"code": "ACCOUNT_PENDING", "message": "Your account is awaiting HOD approval."}
                )
            elif self.user.status == User.Status.REJECTED:
                raise serializers.ValidationError(
                    {"code": "ACCOUNT_REJECTED", "message": "Your registration was rejected."}
                )
            else:
                raise serializers.ValidationError(
                    {"code": "FORBIDDEN", "message": "Your account is suspended."}
                )

        data["user"] = UserSerializer(self.user).data
        return data


class ProfileUpdateSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField(read_only=True)
    employee_code = serializers.SerializerMethodField(read_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ["username", "role", "first_name", "last_name", "email", "department", "employee_code", "phone"]
        read_only_fields = ["username", "role", "department", "employee_code"]

    def get_department(self, obj):
        profile = getattr(obj, "employee_profile", None)
        return profile.department.name if profile else None

    def get_employee_code(self, obj):
        profile = getattr(obj, "employee_profile", None)
        return profile.employee_code if profile else None

    def update(self, instance, validated_data):
        phone = validated_data.pop("phone", None)
        changed = []
        for key, value in validated_data.items():
            if getattr(instance, key) != value:
                setattr(instance, key, value); changed.append(key)
        if changed:
            instance.save(update_fields=changed)
        if phone is not None and hasattr(instance, "employee_profile") and instance.employee_profile.phone != phone:
            instance.employee_profile.phone = phone
            instance.employee_profile.save(update_fields=["phone"])
        return instance
