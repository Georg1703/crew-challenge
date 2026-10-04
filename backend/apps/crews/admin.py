from django.contrib import admin

from .models import Crew, Invite, Member


class MemberInline(admin.TabularInline):
    model = Member
    extra = 0
    fields = ("display_name", "user", "role")
    ordering = ("created_at",)


@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    list_display = ("name", "timezone", "created_at")
    search_fields = ("name",)
    inlines = [MemberInline]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("display_name", "crew", "user", "role", "created_at")
    list_filter = ("crew", "role")
    search_fields = ("display_name", "user__username")


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ("code", "crew", "created_by", "expires_at", "used_by", "used_at")
    list_filter = ("crew",)
    readonly_fields = ("used_by", "used_at")
