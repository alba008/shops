from django.contrib import admin
from .models import Enquiry

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "subject", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("email", "subject", "message")
    ordering = ("-id",)
