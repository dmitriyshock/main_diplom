from functools import wraps
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
def get_role(user):
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role
    except Exception:
        return 'employee'


def crm_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/crm/login/?next={request.path}')
        try:
            profile = request.user.profile
        except Exception:
            profile = None
        if profile is not None and not profile.is_active:
            logout(request)
            return HttpResponseForbidden("Доступ к CRM отключён")
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/crm/login/?next={request.path}')
        role = get_role(request.user)
        if role not in ('admin', 'manager'):
            return HttpResponseForbidden("Недостаточно прав")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/crm/login/?next={request.path}')
        if get_role(request.user) != 'admin':
            return HttpResponseForbidden("Только для администраторов")
        return view_func(request, *args, **kwargs)
    return wrapper
