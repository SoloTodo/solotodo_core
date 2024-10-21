from collections import defaultdict
from datetime import timedelta

import requests
from dateutil import parser
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.db.models.functions import TruncDate
from requests.auth import HTTPBasicAuth

from solotodo.models import Entity, Product


class StaffActivityForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()
    staff = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        from django.conf import settings

        super().__init__(*args, **kwargs)
        staff_choices = get_user_model().objects.filter(
            pk__in=settings.STAFF_EXTERNAL_SERVICES_IDS.keys()
        )
        self.fields["staff"].queryset = staff_choices

    def clean_end_date(self):
        start_date = self.cleaned_data["start_date"]
        end_date = self.cleaned_data["end_date"]
        if end_date < start_date:
            raise ValidationError("End date must be greater than start date")
        return end_date

    def get_data(self):
        result = []

        disqus_data = self.get_disqus_data()
        zendesk_data = self.get_zendesk_data()
        associated_entities_data = self.get_associated_entities_data()
        created_products_data = self.get_created_products_data()

        date_iterator = self.cleaned_data["start_date"]
        while date_iterator <= self.cleaned_data["end_date"]:
            disqus_comments = disqus_data.get(date_iterator, 0)
            zendesk_solved_tickets = zendesk_data.get(date_iterator, 0)
            associated_entities = associated_entities_data.get(date_iterator, 0)
            created_products = created_products_data.get(date_iterator, 0)

            result.append(
                {
                    "date": date_iterator,
                    "disqus_comments": disqus_comments,
                    "zendesk_solved_tickets": zendesk_solved_tickets,
                    "associated_entities": associated_entities,
                    "created_products": created_products,
                }
            )
            date_iterator += timedelta(days=1)
        return result

    def get_disqus_data(self):
        from django.conf import settings

        result = defaultdict(lambda: 0)
        staff = self.cleaned_data["staff"]
        disqus_username = settings.STAFF_EXTERNAL_SERVICES_IDS[staff.id]["Disqus"]
        cursor = None
        done = False
        while not done:
            # I have no idea why, but the "since" date is the upper date limit
            endpoint = "https://disqus.com/api/3.0/users/listPosts.json?api_key={}&user=username:{}&since={}T00:00:00&limit=100&order=desc".format(
                settings.DISQUS_KEY,
                disqus_username,
                self.cleaned_data["end_date"].isoformat(),
            )
            if cursor:
                endpoint += "&cursor={}".format(cursor)
            response = requests.get(endpoint).json()
            for entry in response["response"]:
                if entry["forum"] != "solotodo3":
                    continue
                timestamp = parser.parse(entry["createdAt"]).date()
                if timestamp < self.cleaned_data["start_date"]:
                    done = True
                    break
                result[timestamp] += 1

            if not response["cursor"]["hasNext"]:
                break
            cursor = response["cursor"]["next"]

        return result

    def get_zendesk_data(self):
        from django.conf import settings

        start_date = self.cleaned_data["start_date"]
        end_date = self.cleaned_data["end_date"]
        staff = self.cleaned_data["staff"]
        zendesk_id = settings.STAFF_EXTERNAL_SERVICES_IDS[staff.id]["Zendesk"]
        next_page_url = f"https://solotodo.zendesk.com/api/v2/search.json?per_page=100&query=type:ticket status>=solved assignee:{zendesk_id} updated>={start_date.isoformat()} updated<={end_date.isoformat()}"
        result = defaultdict(lambda: 0)

        while True:
            response = requests.get(
                next_page_url,
                auth=HTTPBasicAuth(
                    f"{settings.ZENDESK_EMAIL}/token", settings.ZENDESK_API_KEY
                ),
            )

            # Parse the response
            data = response.json()
            for entry in data["results"]:
                timestamp = parser.parse(entry["updated_at"]).date()
                result[timestamp] += 1

            if data["next_page"]:
                next_page_url = data["next_page"]
            else:
                break

        return result

    def get_associated_entities_data(self):
        associated_entities = (
            Entity.objects.filter(
                last_association__gte=self.cleaned_data["start_date"],
                last_association__lte=self.cleaned_data["end_date"],
                last_association_user=self.cleaned_data["staff"],
            )
            .annotate(date=TruncDate("last_association"))
            .order_by("date")
            .values("date")
            .annotate(count=Count("id"))
        )
        result = {x["date"]: x["count"] for x in associated_entities}
        return result

    def get_created_products_data(self):
        created_products = (
            Product.objects.filter(
                creation_date__gte=self.cleaned_data["start_date"],
                creation_date__lte=self.cleaned_data["end_date"],
                creator=self.cleaned_data["staff"],
            )
            .annotate(date=TruncDate("creation_date"))
            .order_by("date")
            .values("date")
            .annotate(count=Count("id"))
        )
        result = {x["date"]: x["count"] for x in created_products}
        return result
