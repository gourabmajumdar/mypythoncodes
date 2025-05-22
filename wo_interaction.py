from django.http import JsonResponse
from django.views import View
from django.db import connection
from services.filemaker_api import FilemakerDataApi
from utils.base_api import BaseAPI
import logging

logger = logging.getLogger(__name__)

class WOInteractionView:

    def get_site_address(self, request):
        query = "SELECT site_id as siteId, site as siteName, address1 as address, address2 as address2,  lower(city) as city, state, zipcode as zip, equipment_needed FROM filemaker2.api_addresses WHERE address1 IS NOT NULL ORDER BY site ASC"
        result = self.query(query)
        return JsonResponse({"result": {"data": {"response": {"data": result}}}})

    def get_contacts(self, request):
        query = "SELECT * FROM filemaker2.api_contacts WHERE status = 1"
        result = self.query(query)
        return JsonResponse({"result": {"data": {"response": {"data": result}}}})

    def get_dns(self, request):
        query = "SELECT id, name FROM filemaker2.api_dns ORDER BY name ASC"
        result = self.query(query)
        return JsonResponse({"result": {"data": {"response": {"data": result}}}})

    def get_projects(self, request):
        query = "SELECT id, name FROM filemaker2.api_projects ORDER BY name ASC"
        result = self.query(query)
        return JsonResponse({"result": {"data": {"response": {"data": result}}}})

    def get_tasks(self, request):
        query = "SELECT * FROM filemaker2.api_tasks ORDER BY name ASC"
        result = self.query(query)
        return JsonResponse({"result": {"data": {"response": {"data": result}}}})

    def get_tasks_new(self, request):
        query = "SELECT * FROM filemaker2.api_tasks_new ORDER BY name ASC"
        result = self.query(query)
        return JsonResponse({"result": {"data": {"response": {"data": result}}}})

    def get_wo(self, request):
        wo_id = request.GET.get("wo_id")
        if not wo_id:
            return JsonResponse({"error": "Missing wo_id"}, status=400)

        api = FilemakerDataApi()
        token_info = api.get_token()
        token = token_info['data']['response']['token']

        payload = {
            "query": [{"WOPrefix_Number": f"WO-{wo_id}"}]
        }
        response = api.query_layout("API_NetEngWO", token, payload)
        return JsonResponse({"result": response})

    def get_attachments(self, request):
        query = "SELECT * FROM filemaker2.api_attachments ORDER BY created_at DESC"
        result = self.query(query)
        return JsonResponse({"result": {"data": {"response": {"data": result}}}})

    def query(self, sql, params=None):
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])
            desc = [col[0] for col in cursor.description]
            return [dict(zip(desc, row)) for row in cursor.fetchall()]
