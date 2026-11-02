from unittest.mock import Mock, patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase

from backend.core.service.clients.validate import validate_client, validate_client_create


class ValidateClientCreateTests(SimpleTestCase):
    def test_valid_client_details_return_no_error(self):
        self.assertIsNone(
            validate_client_create(
                {
                    "name": "Acme",
                    "address": "123",
                }
            )
        )

    def test_address_length_boundaries_are_valid(self):
        for address in ("a" * 3, "a" * 84):
            with self.subTest(length=len(address)):
                self.assertIsNone(validate_client_create({"name": "Acme", "address": address}))

    def test_invalid_client_details_return_expected_errors(self):
        cases = (
            ({}, "Please provide at least a client name"),
            ({"name": "AB"}, "Client name must be at least 3 characters"),
            ({"name": "Acme", "is_representative": True}, "Please provide a company name if you are creating a representative"),
            ({"name": "Acme", "address": "ab"}, "Please provide a valid address between 3 and 84 characters"),
            ({"name": "Acme", "address": "a" * 85}, "Please provide a valid address between 3 and 84 characters"),
        )

        for details, expected_error in cases:
            with self.subTest(details=details):
                self.assertEqual(validate_client_create(details), expected_error)


class ValidateClientTests(SimpleTestCase):
    def test_invalid_client_id_raises_validation_error(self):
        with self.assertRaisesMessage(ValidationError, "Invalid client ID"):
            validate_client(Mock(user=Mock()), "not-an-id")

    def test_fake_queryset_with_defaults_checks_access(self):
        request = Mock(user=Mock())
        client = Mock()
        client.has_access.return_value = True
        queryset = Mock()
        queryset.select_related.return_value = queryset
        queryset.get.return_value = client

        with patch("backend.core.service.clients.validate.Client.objects") as objects:
            objects.all.return_value = queryset

            result = validate_client(request, "42", get_defaults=True)

        self.assertIs(result, client)
        objects.all.assert_called_once_with()
        queryset.select_related.assert_called_once_with("default_values")
        queryset.get.assert_called_once_with(id=42)
        client.has_access.assert_called_once_with(request.user)

    def test_client_without_access_raises_permission_denied(self):
        request = Mock(user=Mock())
        client = Mock()
        client.has_access.return_value = False
        queryset = Mock()
        queryset.get.return_value = client

        with patch("backend.core.service.clients.validate.Client.objects") as objects:
            objects.all.return_value = queryset

            with self.assertRaises(PermissionDenied):
                validate_client(request, 42)
