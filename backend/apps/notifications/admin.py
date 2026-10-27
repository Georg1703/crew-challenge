from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("kind", "recipient", "actor", "target_id", "read_at", "crew", "created_at")
    list_filter = ("crew", "kind")
    raw_id_fields = ("recipient", "actor")


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "user_agent", "created_at", "updated_at")
    raw_id_fields = ("user",)
