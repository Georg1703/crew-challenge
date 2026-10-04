from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        *(DjangoUserAdmin.fieldsets or ()),
        ("Preferences", {"fields": ("preferred_language",)}),
    )
    list_display = ("username", "email", "preferred_language", "is_staff", "date_joined")
