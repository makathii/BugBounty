from django.contrib import admin
from .models import BugReport, Comment

@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ('title','reporter','severity','status','created_at')
    list_filter = ('status','severity','created_at')
    search_fields = ('title','description','reporter__username')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('report','author','parent','is_internal','created_at')
    list_filter = ('is_internal',)
    search_fields = ('text','author__username')
