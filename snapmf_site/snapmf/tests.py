import json
from http import HTTPStatus
from uuid import UUID
from unittest.mock import patch

from django.shortcuts import resolve_url
from django.test import TestCase

from .models import Job, Status


def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.

     Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

     Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

     Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """

    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


class SimpleViewTests(TestCase):
    """
    Simple tests to make sure the URLs for each "simple" webpage is where
    it should be.
    """

    def test_dashboard(self):
        response = self.client.get(resolve_url("snapmf:dashboard"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_docs(self):
        response = self.client.get(resolve_url("snapmf:docs"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_handle_snapms_is_not_get(self):
        response = self.client.get(resolve_url("snapmf:handle_snapms"))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_handle_snapms_is_post(self):
        from django.http import HttpResponse

        with patch("snapms_site.snapmf.views.handle_snapms_request") as mock_fn:
            mock_fn.return_value = HttpResponse(dict(success=True))
            response = self.client.post(resolve_url("snapmf:handle_snapms"))
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_handle_snapms_bad_fileformat(self):
        from django.http import HttpResponseBadRequest

        with patch("snapms_site.snapmf.views.handle_snapms_request") as mock_fn:
            mock_fn.return_value = HttpResponseBadRequest()
            response = self.client.post(resolve_url("snapmf:handle_snapms"))
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)


class JobModelTests(TestCase):
    def test_job_creates_uuid(self):
        job = Job.objects.create(
            inputfile="test",
            parameters=json.dumps({"test": "test"}),
        )
        self.assert_(is_valid_uuid(job.id))

    def test_job_create_sets_status_queued(self):
        job = Job.objects.create(
            inputfile="test",
            parameters=json.dumps({"test": "test"}),
        )
        self.assertEqual(job.status, Status.queued.value)


# class HelperFunctionTests(TestCase):
#     def test_
