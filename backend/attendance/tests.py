from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from company.models import Company
from .models import AttendanceDay
from .services import InvalidPunchError, create_punch, recalculate_day


class AttendanceServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="attendance-user",
            password="StrongPass123!",
            status=User.Status.ACTIVE,
        )
        self.company = Company.get_solo()
        self.company.standard_break_minutes = 60
        self.company.standard_shift_minutes = 480
        self.company.shift_start_time = time(9, 0)
        self.company.save()

    def _at(self, hour, minute=0):
        naive = datetime.combine(timezone.localdate(), time(hour, minute))
        return timezone.make_aware(naive)

    def test_single_pair_deducts_configured_break(self):
        create_punch(self.user, self._at(9, 0))
        create_punch(self.user, self._at(18, 0))
        day = AttendanceDay.objects.get(employee=self.user, date=timezone.localdate())
        self.assertEqual(day.punch_count, 2)
        self.assertEqual(day.total_minutes, 480)
        self.assertEqual(day.break_minutes, 60)
        self.assertEqual(day.overtime_minutes, 0)
        self.assertEqual(day.status, AttendanceDay.Status.PRESENT)

    def test_multiple_pairs_do_not_double_deduct_break(self):
        create_punch(self.user, self._at(9, 0))
        create_punch(self.user, self._at(12, 0))
        create_punch(self.user, self._at(13, 0))
        create_punch(self.user, self._at(18, 0))
        day = AttendanceDay.objects.get(employee=self.user, date=timezone.localdate())
        self.assertEqual(day.total_minutes, 480)
        self.assertEqual(day.break_minutes, 0)

    def test_unmatched_in_is_incomplete_and_has_no_fake_out(self):
        create_punch(self.user, self._at(9, 0))
        day = AttendanceDay.objects.get(employee=self.user, date=timezone.localdate())
        self.assertEqual(day.status, AttendanceDay.Status.INCOMPLETE)
        self.assertIsNotNone(day.first_in)
        self.assertIsNone(day.last_out)

    def test_duplicate_punch_is_rejected(self):
        when = self._at(9, 0)
        create_punch(self.user, when)
        with self.assertRaises(InvalidPunchError) as ctx:
            create_punch(self.user, when + timedelta(seconds=10))
        self.assertEqual(ctx.exception.code, "DUPLICATE_REQUEST")
