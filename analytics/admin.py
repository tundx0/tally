from django.contrib import admin

from .models import Event, Person, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "api_key", "created_at"]
    readonly_fields = ["api_key"]
    filter_horizontal = ["members"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["distinct_id", "project", "created_at"]
    list_filter = ["project"]
    list_select_related = ["project"]
    search_fields = ["distinct_id"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["event", "distinct_id", "project", "timestamp"]
    list_filter = ["project", "event"]
    list_select_related = ["project"]
    search_fields = ["distinct_id"]
    date_hierarchy = "timestamp"
    # COUNT(*) on a huge table is slow; skip it on filtered pages.
    show_full_result_count = False
