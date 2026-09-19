from django.test import Client, TestCase
from django.urls import reverse

from crm.models import Appointment, Branch
from .models import Brand, PhoneModel, RepairService, Review


class PublicHomepageTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='Apple', is_active=True)
        self.model = PhoneModel.objects.create(brand=self.brand, name='iPhone 15', is_active=True)
        self.service = RepairService.objects.create(
            phone_model=self.model, name='Замена дисплея', price_from=12000,
            is_active=True, is_popular=True,
        )
        self.branch = Branch.objects.create(name='Центр', is_active=True)

    def test_home_renders_only_public_active_data_and_brands(self):
        inactive_brand = Brand.objects.create(name='Hidden brand', is_active=False)
        inactive_model = PhoneModel.objects.create(
            brand=inactive_brand, name='Hidden phone', is_active=True,
        )
        RepairService.objects.create(
            phone_model=inactive_model, name='Hidden service', price_from=1,
            is_active=True, is_popular=True,
        )
        Review.objects.create(author='Алина', text='Всё хорошо', is_active=True)
        Review.objects.create(author='Скрытый', text='Не показывать', is_active=False)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['brands'], [self.brand])
        self.assertQuerySetEqual(response.context['popular_services'], [self.service])
        self.assertQuerySetEqual(response.context['reviews'], [Review.objects.get(author='Алина')])
        self.assertQuerySetEqual(response.context['branches'], [self.branch])
        self.assertContains(response, 'Apple')
        self.assertContains(response, 'iPhone 15')
        self.assertContains(response, 'Замена дисплея')
        self.assertNotContains(response, 'Hidden brand')
        self.assertNotContains(response, 'Hidden service')

    def test_booking_ajax_creates_appointment_with_active_branch(self):
        response = self.client.post(
            reverse('contact_request'),
            {'name': 'Иван', 'phone': 'vk.com/id1', 'device': 'iPhone 15',
             'message': 'Не включается', 'branch_id': self.branch.pk},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'ok': True})
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.name, 'Иван')
        self.assertEqual(appointment.phone, 'vk.com/id1')
        self.assertEqual(appointment.device, 'iPhone 15')
        self.assertEqual(appointment.problem, 'Не включается')
        self.assertEqual(appointment.source, 'website')
        self.assertEqual(appointment.branch, self.branch)

    def test_booking_ajax_returns_friendly_400_for_required_or_too_long_values(self):
        empty = self.client.post(
            reverse('contact_request'), {'name': '', 'phone': ''},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        too_long = self.client.post(
            reverse('contact_request'), {'name': 'Иван', 'phone': 'x' * 31},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.json()['error'], 'Укажите имя и телефон или ВКонтакте.')
        self.assertEqual(too_long.status_code, 400)
        self.assertEqual(too_long.json()['error'], 'Контакт слишком длинный.')
        self.assertEqual(Appointment.objects.count(), 0)

    def test_booking_allows_blank_branch_but_rejects_invalid_or_inactive_branch(self):
        inactive_branch = Branch.objects.create(name='Закрыт', is_active=False)
        blank = self.client.post(
            reverse('contact_request'), {'name': 'Иван', 'phone': '+79990000000', 'branch_id': ''},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(blank.status_code, 200)
        for branch_id in ('not-an-id', str(inactive_branch.pk)):
            response = self.client.post(
                reverse('contact_request'), {'name': 'Иван', 'phone': '+79990000000', 'branch_id': branch_id},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.json()['error'],
                'Выбранный филиал недоступен. Выберите другой или оставьте поле пустым.',
            )

        self.assertEqual(Appointment.objects.count(), 1)
        self.assertTrue(all(appt.branch is None for appt in Appointment.objects.all()))

    def test_booking_requires_a_valid_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        rejected = csrf_client.post(
            reverse('contact_request'), {'name': 'Иван', 'phone': '+79990000000'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(Appointment.objects.count(), 0)

        csrf_client.get(reverse('home'))
        accepted = csrf_client.post(
            reverse('contact_request'), {'name': 'Иван', 'phone': '+79990000000'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_X_CSRFTOKEN=csrf_client.cookies['csrftoken'].value,
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_non_ajax_redirect_does_not_follow_external_referer(self):
        response = self.client.post(
            reverse('contact_request'), {'name': 'Иван', 'phone': '+79990000000'},
            HTTP_REFERER='https://attacker.example/next',
        )

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_prices_searches_by_brand_and_hides_inactive_brand_data(self):
        response = self.client.get(reverse('prices'), {'q': 'Apple'})

        self.assertEqual(response.status_code, 200)
        result = response.context['result']
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['brand'], self.brand)
        self.assertEqual(result[0]['models'][0]['services'], [self.service])

    def test_public_price_apis_hide_inactive_brand_data(self):
        hidden_brand = Brand.objects.create(name='Hidden', is_active=False)
        hidden_model = PhoneModel.objects.create(brand=hidden_brand, name='H1', is_active=True)
        RepairService.objects.create(phone_model=hidden_model, name='Hidden repair', price_from=1, is_active=True)

        prices = self.client.get(reverse('api_prices'))
        visible_models = self.client.get(reverse('api_models', args=[self.brand.pk]))
        hidden_models = self.client.get(reverse('api_models', args=[hidden_brand.pk]))

        self.assertEqual([item['name'] for item in prices.json()], ['Замена дисплея'])
        self.assertEqual(visible_models.json(), [{'id': self.model.pk, 'name': 'iPhone 15'}])
        self.assertEqual(hidden_models.json(), [])
