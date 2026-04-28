from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import format_brl_amount, parse_brl_amount
from .models import Goal, GoalContribution

User = get_user_model()


class BRLParserTests(TestCase):
    def test_parses_brazilian_format(self):
        self.assertEqual(parse_brl_amount('1.234,56'), Decimal('1234.56'))

    def test_parses_simple_decimal(self):
        self.assertEqual(parse_brl_amount('500,00'), Decimal('500.00'))

    def test_parses_dot_decimal(self):
        self.assertEqual(parse_brl_amount('1234.56'), Decimal('1234.56'))

    def test_parses_with_currency_prefix(self):
        self.assertEqual(parse_brl_amount('R$ 1.000,00'), Decimal('1000.00'))

    def test_empty_returns_none(self):
        self.assertIsNone(parse_brl_amount(''))
        self.assertIsNone(parse_brl_amount(None))

    def test_invalid_raises_validation_error(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            parse_brl_amount('abc')

    def test_format_brl_amount(self):
        self.assertEqual(format_brl_amount(Decimal('1234.56')), '1.234,56')
        self.assertEqual(format_brl_amount(Decimal('0.00')), '0,00')
        self.assertEqual(format_brl_amount(None), '')


class GoalModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='pw12345!'
        )

    def _make_goal(self, **overrides):
        defaults = dict(
            user=self.user,
            name='Reserva de Emergência',
            target_amount=Decimal('1000.00'),
        )
        defaults.update(overrides)
        return Goal.objects.create(**defaults)

    def test_create_with_valid_data(self):
        goal = self._make_goal()
        self.assertEqual(goal.current_amount, Decimal('0.00'))
        self.assertEqual(goal.status, Goal.STATUS_ACTIVE)

    def test_target_amount_must_be_positive(self):
        goal = Goal(user=self.user, name='X', target_amount=Decimal('0.00'))
        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_name_is_required(self):
        goal = Goal(user=self.user, name='   ', target_amount=Decimal('100'))
        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_past_deadline_rejected_on_create(self):
        goal = Goal(
            user=self.user,
            name='Atrasada',
            target_amount=Decimal('100'),
            deadline=date.today() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_progress_pct_caps_at_100(self):
        goal = self._make_goal(target_amount=Decimal('100'))
        goal.current_amount = Decimal('250')
        self.assertEqual(goal.progress_pct, Decimal('100.00'))


class GoalContributionSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bob', email='bob@example.com', password='pw12345!'
        )
        self.goal = Goal.objects.create(
            user=self.user,
            name='Viagem',
            target_amount=Decimal('1000.00'),
        )

    def _make_contribution(self, amount):
        return GoalContribution.objects.create(
            goal=self.goal,
            user=self.user,
            amount=Decimal(amount),
            date=date.today(),
        )

    def test_contribution_updates_current_amount(self):
        self._make_contribution('200.00')
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('200.00'))

    def test_multiple_contributions_sum(self):
        self._make_contribution('200.00')
        self._make_contribution('300.50')
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('500.50'))

    def test_deleting_contribution_recalculates(self):
        c1 = self._make_contribution('200.00')
        self._make_contribution('300.00')
        c1.delete()
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('300.00'))

    def test_status_becomes_completed_when_target_reached(self):
        self._make_contribution('1000.00')
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.status, Goal.STATUS_COMPLETED)

    def test_status_returns_to_active_after_removal(self):
        c1 = self._make_contribution('1000.00')
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.status, Goal.STATUS_COMPLETED)
        c1.delete()
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.status, Goal.STATUS_ACTIVE)

    def test_cancelled_status_preserved_when_recalculating(self):
        self.goal.status = Goal.STATUS_CANCELLED
        self.goal.save()
        self._make_contribution('200.00')
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.status, Goal.STATUS_CANCELLED)


class GoalContributionValidationTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='ua', email='ua@example.com', password='pw12345!'
        )
        self.user_b = User.objects.create_user(
            username='ub', email='ub@example.com', password='pw12345!'
        )
        self.goal_a = Goal.objects.create(
            user=self.user_a, name='A', target_amount=Decimal('500')
        )

    def test_contribution_user_must_match_goal_user(self):
        contribution = GoalContribution(
            goal=self.goal_a,
            user=self.user_b,
            amount=Decimal('50'),
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            contribution.full_clean()

    def test_contribution_amount_must_be_positive(self):
        contribution = GoalContribution(
            goal=self.goal_a,
            user=self.user_a,
            amount=Decimal('0'),
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            contribution.full_clean()


class GoalViewIsolationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username='alice', email='alice@example.com', password='pw12345!'
        )
        self.bob = User.objects.create_user(
            username='bob', email='bob@example.com', password='pw12345!'
        )
        self.alice_goal = Goal.objects.create(
            user=self.alice, name='Alice meta', target_amount=Decimal('500')
        )

    def test_other_user_cannot_view_detail(self):
        self.client.force_login(self.bob)
        response = self.client.get(
            reverse('goals:detail', args=[self.alice_goal.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_edit(self):
        self.client.force_login(self.bob)
        response = self.client.get(
            reverse('goals:edit', args=[self.alice_goal.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse('goals:delete', args=[self.alice_goal.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Goal.objects.filter(pk=self.alice_goal.pk).exists())

    def test_other_user_cannot_contribute(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse('goals:contribute', args=[self.alice_goal.pk]),
            data={'amount': '50.00', 'date': date.today().isoformat(), 'notes': ''},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.alice_goal.contributions.count(), 0)

    def test_list_only_shows_own_goals(self):
        Goal.objects.create(
            user=self.bob, name='Bob meta', target_amount=Decimal('300')
        )
        self.client.force_login(self.alice)
        response = self.client.get(reverse('goals:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice meta')
        self.assertNotContains(response, 'Bob meta')

    def test_create_assigns_current_user(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse('goals:create'),
            data={
                'name': 'Nova meta',
                'description': '',
                'target_amount': '750.00',
                'deadline': '',
                'icon': '🎯',
                'color': '#3B82F6',
            },
        )
        self.assertEqual(response.status_code, 302)
        goal = Goal.objects.get(name='Nova meta')
        self.assertEqual(goal.user, self.alice)

    def test_create_accepts_brazilian_currency_format(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse('goals:create'),
            data={
                'name': 'Meta BRL',
                'description': '',
                'target_amount': '1.234,56',
                'deadline': '',
                'icon': '🎯',
                'color': '#3B82F6',
            },
        )
        self.assertEqual(response.status_code, 302)
        goal = Goal.objects.get(name='Meta BRL')
        self.assertEqual(goal.target_amount, Decimal('1234.56'))

    def test_contribution_accepts_brazilian_currency_format(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse('goals:contribute', args=[self.alice_goal.pk]),
            data={
                'amount': '1.500,00',
                'date': date.today().isoformat(),
                'notes': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        contribution = self.alice_goal.contributions.get()
        self.assertEqual(contribution.amount, Decimal('1500.00'))
