"""Authenticated GET smoke coverage for every argument-free CRM URL.

The suite deliberately skips handlers whose GET request changes business state
(`logout` and `sale_create`).  File-manager storage is redirected to a temporary
directory so the suite uses neither the deployed database nor its files.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.test import TestCase

from crm import views
from crm.urls import urlpatterns


SKIPPED_STATE_CHANGING_GETS = {"logout", "sale_create"}
ADMIN_OR_MANAGER_ONLY = {
    "branch_list", "branch_save", "employee_list", "employee_create",
    "user_list", "user_create", "settings_company", "filemanager",
    "filemanager_upload", "filemanager_rename", "filemanager_download",
    "filemanager_mkdir", "filemanager_delete", "price_service_save",
    "price_model_save", "price_brand_save",
    "finance", "analytics", "expense_create",
}
GET_REDIRECTS = {
    "login", "branch_save", "filemanager_upload", "filemanager_rename",
    "filemanager_mkdir", "filemanager_delete", "price_service_save",
    "price_model_save", "price_brand_save",
}
GET_METHOD_NOT_ALLOWED = {"expense_create", "task_create"}
GET_NOT_FOUND_WITHOUT_QUERY = {"filemanager_download"}


class CrmAuthenticatedGetSmokeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage_tmp = TemporaryDirectory()
        cls.original_storage_root = views.STORAGE_ROOT
        views.STORAGE_ROOT = Path(cls.storage_tmp.name)

    @classmethod
    def tearDownClass(cls):
        views.STORAGE_ROOT = cls.original_storage_root
        cls.storage_tmp.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.admin = User.objects.create_superuser("smoke-admin", "", "secret")
        self.employee = User.objects.create_user("smoke-employee", password="secret")

    @staticmethod
    def route_names():
        """Named CRM routes that can be requested without path arguments."""
        return {
            pattern.name
            for pattern in urlpatterns
            if pattern.name and "<" not in str(pattern.pattern)
        }

    def test_route_inventory_is_explicit(self):
        classified = (
            SKIPPED_STATE_CHANGING_GETS | ADMIN_OR_MANAGER_ONLY | GET_REDIRECTS
            | GET_METHOD_NOT_ALLOWED | GET_NOT_FOUND_WITHOUT_QUERY
        )
        self.assertEqual(self.route_names(), classified | {
            "dashboard", "search", "customer_list", "customer_create",
            "customer_search_api", "repair_list", "repair_create",
            "models_by_brand_api", "warehouse_parts", "part_create",
            "warehouse_accessories", "accessory_create", "stock_movements",
            "supplier_list", "sale_list", "finance", "payroll_my", "analytics",
            "task_list", "my_profile", "notifications", "document_list",
            "appointment_list", "appointment_create", "call_request_list",
            "price_list",
        })

    def test_admin_gets_expected_non_error_response_for_every_safe_route(self):
        self.client.force_login(self.admin)
        for name in self.route_names() - SKIPPED_STATE_CHANGING_GETS:
            with self.subTest(route=name):
                response = self.client.get(f"/crm/{self._suffix(name)}")
                if name in GET_REDIRECTS:
                    self.assertEqual(response.status_code, 302)
                elif name in GET_METHOD_NOT_ALLOWED:
                    self.assertEqual(response.status_code, 405)
                elif name in GET_NOT_FOUND_WITHOUT_QUERY:
                    self.assertEqual(response.status_code, 404)
                else:
                    self.assertEqual(response.status_code, 200)

    def test_employee_is_forbidden_only_from_privileged_routes_and_no_safe_get_500s(self):
        self.client.force_login(self.employee)
        for name in self.route_names() - SKIPPED_STATE_CHANGING_GETS:
            with self.subTest(route=name):
                response = self.client.get(f"/crm/{self._suffix(name)}")
                if name in ADMIN_OR_MANAGER_ONLY:
                    self.assertEqual(response.status_code, 403)
                elif name in GET_REDIRECTS:
                    self.assertEqual(response.status_code, 302)
                elif name in GET_METHOD_NOT_ALLOWED:
                    self.assertEqual(response.status_code, 405)
                elif name in GET_NOT_FOUND_WITHOUT_QUERY:
                    self.assertEqual(response.status_code, 404)
                else:
                    self.assertEqual(response.status_code, 200)

    @staticmethod
    def _suffix(name):
        """Use the URL pattern itself so the inventory test covers the actual route."""
        for pattern in urlpatterns:
            if pattern.name == name:
                return str(pattern.pattern)
        raise AssertionError(f"Unknown CRM route: {name}")
