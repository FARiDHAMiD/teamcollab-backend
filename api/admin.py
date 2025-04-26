from django.contrib import admin
from .models import User, Task, Comment, Notification
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Custom User Admin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'dob', 'phone')}),
    )
    list_display = ('username', 'email', 'role', 'dob', 'phone', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'role')
    ordering = ('id',)

# Task Admin
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'created_by', 'created_at')
    list_filter = ('status', 'priority', 'created_by')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)

# Comment Admin
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'task', 'created_at')
    list_filter = ('author', 'task')
    search_fields = ('content',)
    ordering = ('-created_at',)

# Notification Admin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'recipient')
    search_fields = ('message',)
    ordering = ('-created_at',)
