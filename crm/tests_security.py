"""Regression coverage for the CRM authorization hardening package."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from crm.models import Appointment, Branch, Customer, Expense, SaleOrder, UserProfile


class CrmSecurityRegressionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('security-admin', password='admin-password')
        self.manager = User.objects.create_user('security-manager', password='manager-password')
        self.employee = User.objects.create_user('security-employee', password='employee-password')
        for user, role in (
            (self.admin, 'admin'),
            (self.manager, 'manager'),
            (self.employee, 'employee'),
        ):
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save(update_fields=['role'])

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            reverse('crm:login'),
            {
                'username': self.employee.username,
                'password': 'employee-password',
                'next': 'https://attacker.example/landing',
            },
        )

        self.assertRedirects(response, reverse('crm:dashboard'), fetch_redirect_response=False)

    def test_inactive_profile_is_denied_crm_access(self):
        self.employee.profile.is_active = False
        self.employee.profile.save(update_fields=['is_active'])
        self.client.force_login(self.employee)

        response = self.client.get(reverse('crm:dashboard'))

        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_access_user_management(self):
        self.client.force_login(self.manager)
        user_count = User.objects.count()

        self.assertEqual(self.client.get(reverse('crm:employee_list')).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse('crm:employee_create'),
                {'username': 'forbidden-user', 'password': 'forbidden-password', 'role': 'admin'},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse('crm:employee_edit', args=[self.admin.pk]),
                {'role': 'employee', 'new_password': 'manager-controlled'},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(reverse('crm:employee_delete', args=[self.employee.pk])).status_code,
            403,
        )
        self.admin.refresh_from_db()
        self.assertEqual(User.objects.count(), user_count)
        self.assertEqual(self.admin.profile.role, 'admin')
        self.assertTrue(self.admin.check_password('admin-password'))

    def test_finance_and_analytics_require_manager_role(self):
        self.client.force_login(self.employee)
        expense_count = Expense.objects.count()

        self.assertEqual(self.client.get(reverse('crm:finance')).status_code, 403)
        self.assertEqual(self.client.get(reverse('crm:analytics')).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse('crm:expense_create'),
                {'category': 'other', 'description': 'blocked', 'amount': '100'},
            ).status_code,
            403,
        )
        self.assertEqual(Expense.objects.count(), expense_count)

        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse('crm:finance')).status_code, 200)
        self.assertEqual(self.client.get(reverse('crm:analytics')).status_code, 200)

    def test_sale_and_appointment_conversion_do_not_write_on_get(self):
        branch = Branch.objects.create(name='Security branch')
        self.employee.profile.branch = branch
        self.employee.profile.branches.add(branch)
        self.employee.profile.save(update_fields=['branch'])
        appointment = Appointment.objects.create(name='Client', phone='+79990000000', branch=branch)
        self.client.force_login(self.employee)
        sale_count = SaleOrder.objects.count()
        customer_count = Customer.objects.count()

        self.assertEqual(self.client.get(reverse('crm:sale_create')).status_code, 405)
        self.assertEqual(
            self.client.get(reverse('crm:appointment_to_order', args=[appointment.pk])).status_code,
            405,
        )
        self.assertEqual(SaleOrder.objects.count(), sale_count)
        self.assertEqual(Customer.objects.count(), customer_count)

        self.assertEqual(self.client.post(reverse('crm:sale_create')).status_code, 302)
        self.assertEqual(
            self.client.post(reverse('crm:appointment_to_order', args=[appointment.pk])).status_code,
            302,
        )
        self.assertEqual(SaleOrder.objects.count(), sale_count + 1)
        self.assertEqual(Customer.objects.count(), customer_count + 1)

    def test_logout_requires_post(self):
        self.client.force_login(self.employee)

        self.assertEqual(self.client.get(reverse('crm:logout')).status_code, 405)
        response = self.client.post(reverse('crm:logout'))

        self.assertRedirects(response, reverse('crm:login'), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('crm:dashboard')).status_code, 302)
