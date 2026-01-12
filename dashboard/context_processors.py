# dashboard/context_processors.py
def workspace_plan(request):
    """
    Add workspace and active plan to all template contexts
    """
    if request.user.is_authenticated:
        from accounts.models import Workspace
        try:
            ws = Workspace.objects.filter(owner=request.user).order_by('-created_at').first()
            if ws:
                return {
                    'workspace': ws,
                    'plan': ws.active_plan,
                }
        except Exception:
            pass
    
    return {
        'workspace': None,
        'plan': None,
    }
