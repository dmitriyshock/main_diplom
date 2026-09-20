from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Brand, PhoneModel
from crm.models import (
    Accessory, Appointment, Branch, Customer, Part, PaymentRecord,
    RepairOrder, RepairOrderAccessory, RepairOrderPart, SaleOrder,
    SaleOrderItem, StockMovement, Task,
)


class BranchAndBusinessIntegrityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('integrity-admin', '', 'secret')
        self.employee = User.objects.create_user('integrity-employee', password='secret')
        self.branch_a = Branch.objects.create(name='Integrity A')
        self.branch_b = Branch.objects.create(name='Integrity B')
        self.employee.profile.branch = self.branch_a
        self.employee.profile.branches.add(self.branch_a)
        self.employee.profile.save()
        self.brand = Brand.objects.create(name='Integrity Brand')
        self.model = PhoneModel.objects.create(brand=self.brand, name='Integrity Model')
        self.customer = Customer.objects.create(name='Integrity Customer', phone='+79990000001')

    def repair(self, **kwargs):
        values = {'customer': self.customer, 'brand': self.brand, 'phone_model': self.model}
        values.update(kwargs)
        return RepairOrder.objects.create(**values)

    def test_employee_cannot_access_another_branch_repair_or_appointment(self):
        repair = self.repair(branch=self.branch_b)
        appointment = Appointment.objects.create(name='Other branch', phone='+79990000002', branch=self.branch_b)
        self.client.force_login(self.employee)

        self.assertEqual(self.client.get(f'/crm/repairs/{repair.pk}/').status_code, 404)
        self.assertEqual(
            self.client.post(f'/crm/repairs/{repair.pk}/status/', {'status': 'done'}).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(f'/crm/appointments/{appointment.pk}/status/', {'status': 'cancelled'}).status_code,
            404,
        )

    def test_repair_prefill_does_not_expose_another_branch_customer(self):
        other_customer = Customer.objects.create(
            name='Private customer', phone='+79990000020', branch=self.branch_b,
        )
        self.client.force_login(self.employee)

        response = self.client.get(f'/crm/repairs/new/?customer_id={other_customer.pk}')

        self.assertEqual(response.status_code, 404)

    def test_repair_assignment_rejects_other_branch_and_inactive_staff(self):
        repair = self.repair(branch=self.branch_a)
        other_master = User.objects.create_user('other-master', password='secret')
        other_master.profile.role = 'master'
        other_master.profile.branch = self.branch_b
        other_master.profile.branches.add(self.branch_b)
        other_master.profile.save()
        inactive_master = User.objects.create_user('inactive-master', password='secret')
        inactive_master.profile.role = 'master'
        inactive_master.profile.branch = self.branch_a
        inactive_master.profile.is_active = False
        inactive_master.profile.branches.add(self.branch_a)
        inactive_master.profile.save()
        self.client.force_login(self.employee)

        self.assertEqual(
            self.client.post(
                f'/crm/repairs/{repair.pk}/assign/', {'assigned_to': other_master.pk},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f'/crm/repairs/{repair.pk}/assign/', {'assigned_to': inactive_master.pk},
            ).status_code,
            404,
        )
        repair.refresh_from_db()
        self.assertIsNone(repair.assigned_to)

    def test_appointment_conversion_keeps_customer_and_form_in_same_branch(self):
        appointment = Appointment.objects.create(
            name='Branch appointment', phone='+79990000021', branch=self.branch_a,
        )
        Customer.objects.create(
            name='Same phone elsewhere', phone=appointment.phone, branch=self.branch_b,
        )
        self.client.force_login(self.employee)

        response = self.client.post(f'/crm/appointments/{appointment.pk}/to-order/')

        self.assertEqual(response.status_code, 302)
        customer = Customer.objects.get(phone=appointment.phone, branch=self.branch_a)
        self.assertIn(f'customer_id={customer.pk}', response.url)
        self.assertIn(f'branch={self.branch_a.pk}', response.url)
        form_response = self.client.get(response.url)
        self.assertEqual(form_response.status_code, 200)
        self.assertEqual(form_response.context['prefill_customer'], customer)
        self.assertEqual(form_response.context['active_branch'], self.branch_a)

        create_response = self.client.post('/crm/repairs/new/', {
            'branch': self.branch_a.pk,
            'customer_id': customer.pk,
            'brand': self.brand.pk,
            'phone_model': self.model.pk,
            'from_appointment': appointment.pk,
        })
        self.assertEqual(create_response.status_code, 302)
        order = RepairOrder.objects.get(customer=customer)
        appointment.refresh_from_db()
        self.assertEqual(order.branch, self.branch_a)
        self.assertEqual(appointment.status, 'completed')
        self.assertEqual(appointment.created_order, order)

    def test_invalid_repair_does_not_create_customer(self):
        self.client.force_login(self.employee)
        customer_count = Customer.objects.count()

        response = self.client.post('/crm/repairs/new/', {
            'branch': self.branch_a.pk,
            'customer_name': 'Premature customer',
            'customer_phone': '+79990000022',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Customer.objects.count(), customer_count)
        self.assertFalse(Customer.objects.filter(phone='+79990000022').exists())

    def test_branchless_appointment_uses_managers_active_branch(self):
        manager = User.objects.create_user('branch-manager', password='secret')
        manager.profile.role = 'manager'
        manager.profile.branch = self.branch_a
        manager.profile.branches.add(self.branch_a)
        manager.profile.save()
        appointment = Appointment.objects.create(
            name='VK lead', phone='+79990000023', source='vk', branch=None,
        )
        self.client.force_login(manager)

        response = self.client.post(f'/crm/appointments/{appointment.pk}/to-order/')

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        customer = Customer.objects.get(phone=appointment.phone, branch=self.branch_a)
        self.assertEqual(appointment.branch, self.branch_a)
        self.assertIn(f'customer_id={customer.pk}', response.url)
        self.assertIn(f'branch={self.branch_a.pk}', response.url)

    def test_payment_decrements_part_and_accessory_once_with_movements(self):
        repair = self.repair(branch=self.branch_a)
        part = Part.objects.create(name='Integrity part', branch=self.branch_a, quantity=1, purchase_price=Decimal('20'))
        accessory = Accessory.objects.create(
            name='Integrity accessory', branch=self.branch_a, quantity=1,
            purchase_price=Decimal('25'), sale_price=Decimal('100'),
        )
        RepairOrderPart.objects.create(order=repair, part=part, quantity=1, price=Decimal('50'))
        RepairOrderAccessory.objects.create(order=repair, accessory=accessory, quantity=1, price=Decimal('100'))
        repair.recalculate_final_cost()
        self.client.force_login(self.admin)

        self.assertEqual(self.client.post(f'/crm/repairs/{repair.pk}/pay/', {'method': 'cash'}).status_code, 302)
        repair.refresh_from_db()
        part.refresh_from_db()
        accessory.refresh_from_db()
        self.assertTrue(repair.is_paid)
        self.assertEqual(part.quantity, 0)
        self.assertEqual(accessory.quantity, 0)
        self.assertEqual(PaymentRecord.objects.filter(repair_order=repair).count(), 1)
        self.assertEqual(StockMovement.objects.filter(movement_type='repair').count(), 2)

        self.assertEqual(self.client.post(f'/crm/repairs/{repair.pk}/pay/', {'method': 'cash'}).status_code, 302)
        self.assertEqual(PaymentRecord.objects.filter(repair_order=repair).count(), 1)
        self.assertEqual(StockMovement.objects.filter(movement_type='repair').count(), 2)

    def test_payment_shortage_leaves_repair_and_stock_unchanged(self):
        repair = self.repair(branch=self.branch_a)
        part = Part.objects.create(name='Short part', branch=self.branch_a, quantity=1)
        RepairOrderPart.objects.create(order=repair, part=part, quantity=2, price=Decimal('50'))
        self.client.force_login(self.admin)

        self.assertEqual(self.client.post(f'/crm/repairs/{repair.pk}/pay/', {'method': 'cash'}).status_code, 302)
        repair.refresh_from_db()
        part.refresh_from_db()
        self.assertFalse(repair.is_paid)
        self.assertEqual(repair.status, 'new')
        self.assertEqual(part.quantity, 1)
        self.assertFalse(PaymentRecord.objects.filter(repair_order=repair).exists())
        self.assertFalse(StockMovement.objects.filter(movement_type='repair').exists())

    def test_paid_repair_rejects_financial_mutation_and_invalid_payment(self):
        repair = self.repair(branch=self.branch_a)
        accessory = Accessory.objects.create(name='Locked accessory', branch=self.branch_a, quantity=1, sale_price=Decimal('100'))
        self.client.force_login(self.admin)

        self.assertEqual(
            self.client.post(f'/crm/repairs/{repair.pk}/pay/', {'method': 'invalid-method'}).status_code,
            302,
        )
        repair.refresh_from_db()
        self.assertFalse(repair.is_paid)

        self.client.post(f'/crm/repairs/{repair.pk}/pay/', {'method': 'cash'})
        self.assertEqual(
            self.client.post(
                f'/crm/repairs/{repair.pk}/add-accessory/',
                {'accessory_id': accessory.pk, 'quantity': 1, 'price': '100'},
            ).status_code,
            302,
        )
        repair.refresh_from_db()
        self.assertEqual(repair.final_cost, Decimal('0'))
        self.assertFalse(RepairOrderAccessory.objects.filter(order=repair).exists())

    def test_finalized_sale_is_immutable_and_validates_line_values(self):
        accessory = Accessory.objects.create(name='Sale accessory', branch=self.branch_a, quantity=1, sale_price=Decimal('100'))
        sale = SaleOrder.objects.create(created_by=self.admin, branch=self.branch_a)
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                f'/crm/sales/{sale.pk}/',
                {'action': 'add_item', 'accessory_id': accessory.pk, 'quantity': 0, 'price': '100'},
            ).status_code,
            302,
        )
        self.assertFalse(SaleOrderItem.objects.filter(order=sale).exists())
        item = SaleOrderItem.objects.create(order=sale, accessory=accessory, quantity=1, price=Decimal('100'))
        sale.recalculate_total()
        self.client.post(f'/crm/sales/{sale.pk}/finalize/')
        self.assertEqual(self.client.post(f'/crm/sales/{sale.pk}/remove-item/{item.pk}/').status_code, 302)
        sale.refresh_from_db()
        self.assertTrue(sale.is_finalized)
        self.assertEqual(sale.total, Decimal('100'))
        self.assertTrue(SaleOrderItem.objects.filter(pk=item.pk).exists())

    def test_task_and_appointment_reject_invalid_status(self):
        task = Task.objects.create(title='Scoped task', branch=self.branch_a)
        appointment = Appointment.objects.create(name='Scoped appointment', phone='+79990000003', branch=self.branch_a)
        self.client.force_login(self.employee)

        self.client.post(f'/crm/tasks/{task.pk}/status/', {'status': 'not-a-status'})
        self.client.post(f'/crm/appointments/{appointment.pk}/status/', {'status': 'not-a-status'})
        task.refresh_from_db()
        appointment.refresh_from_db()
        self.assertEqual(task.status, 'open')
        self.assertEqual(appointment.status, 'new')

    def test_employee_collections_and_search_only_include_active_branch(self):
        own_customer = Customer.objects.create(name='Scope customer A', phone='+79990000011', branch=self.branch_a)
        other_customer = Customer.objects.create(name='Scope customer B', phone='+79990000012', branch=self.branch_b)
        own_part = Part.objects.create(name='Scope part A', branch=self.branch_a)
        Part.objects.create(name='Scope part B', branch=self.branch_b)
        self.repair(customer=own_customer, branch=self.branch_a)
        self.repair(customer=other_customer, branch=self.branch_b)
        self.client.force_login(self.employee)

        customers = self.client.get('/crm/customers/').context['customers']
        parts = self.client.get('/crm/warehouse/parts/').context['parts']
        search = self.client.get('/crm/customers/api/search/?q=Scope').json()
        self.assertEqual({customer.pk for customer in customers}, {own_customer.pk})
        self.assertEqual({part.pk for part in parts}, {own_part.pk})
        self.assertEqual([item['id'] for item in search], [own_customer.pk])

    def test_employee_creates_operational_records_in_active_branch(self):
        self.client.force_login(self.employee)
        self.assertEqual(
            self.client.post('/crm/customers/new/', {'name': 'Created', 'phone': '+79990000013'}).status_code,
            302,
        )
        customer = Customer.objects.get(phone='+79990000013')
        self.assertEqual(customer.branch, self.branch_a)

        part_payload = {
            'name': 'Created part', 'quantity': 1, 'min_quantity': 0,
            'purchase_price': '10', 'sale_price': '20',
        }
        self.assertEqual(self.client.post('/crm/warehouse/parts/new/', part_payload).status_code, 302)
        part = Part.objects.get(name='Created part')
        self.assertEqual(part.branch, self.branch_a)

        self.assertEqual(self.client.post('/crm/sales/new/').status_code, 302)
        self.assertEqual(SaleOrder.objects.get(created_by=self.employee).branch, self.branch_a)
        self.assertEqual(self.client.post('/crm/tasks/create/', {'title': 'Created task'}).status_code, 302)
        self.assertEqual(Task.objects.get(title='Created task').branch, self.branch_a)
