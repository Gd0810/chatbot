from django.contrib import admin

# Adminpanel: Custom actions only (no model registration)
@admin.action(description="Approve selected workspaces")
def approve_workspaces(modeladmin, request, queryset):
    queryset.update(approved=True)

@admin.action(description="Reject selected workspaces") 
def reject_workspaces(modeladmin, request, queryset):
    queryset.update(approved=False)
    

