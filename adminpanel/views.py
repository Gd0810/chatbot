# from django.contrib.admin.views.decorators import staff_member_required
# from django.shortcuts import render, redirect
# from accounts.models import Workspace
# from billing.models import Plan

# @staff_member_required
# def approve_workspace(request, ws_id):
#     ws = Workspace.objects.get(id=ws_id)
#     ws.approved = True
#     ws.save()
#     # Assign default plan
#     Plan.objects.create(workspace=ws, bundle='AI_ONLY')
#     return redirect('adminpanel:dashboard')

# # Add feature flags model/views later

# def dashboard(request):
#     from accounts.models import Workspace
#     from bots.models import Bot
#     workspaces_total = Workspace.objects.count()
#     workspaces_approved = Workspace.objects.filter(approved=True).count()
#     workspaces_pending = Workspace.objects.filter(approved=False).count()
#     bots_total = Bot.objects.count()
#     pending_workspaces = Workspace.objects.filter(approved=False)
#     return render(request, 'adminpanel/dashboard.html', {
#         'workspaces_total': workspaces_total,
#         'workspaces_approved': workspaces_approved,
#         'workspaces_pending': workspaces_pending,
#         'bots_total': bots_total,
#         'pending_workspaces': pending_workspaces
#     })