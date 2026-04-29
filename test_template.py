#!/usr/bin/env python
"""Test script to diagnose template recursion"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'odoo_cafe_pos.settings.local')
django.setup()

from django.test import RequestFactory
from django.template.loader import render_to_string, get_template
from django.urls import resolve
import traceback

# Monkey-patch to trace template rendering
original_render = None
render_stack = []
all_templates = []

def patched_render(self, context):
    template_name = getattr(self, 'origin', None)
    if template_name:
        template_name = str(template_name.name) if hasattr(template_name, 'name') else str(template_name)
    else:
        template_name = 'unknown'
    
    # Simplify path for display
    short_name = template_name.replace('D:\\Odoo X\\Odoo Cafe POS_2\\Odoo Cafe POS\\templates\\', '')
    
    all_templates.append(short_name)
    
    if len(render_stack) > 30:
        print("\n=== RECURSION DETECTED ===")
        print("Full template rendering order:")
        for i, t in enumerate(all_templates):
            print(f"  {i+1}. {t}")
        raise RecursionError(f"Template recursion detected at {short_name}")
    
    render_stack.append(short_name)
    try:
        return original_render(self, context)
    finally:
        render_stack.pop()

def test_template():
    global original_render, all_templates
    
    rf = RequestFactory()
    request = rf.get('/app/pos/')
    
    # Try to get a user
    try:
        from apps.authentication.models import User
        user = User.objects.first()
        if user:
            request.user = user
            print(f"Using user: {user}")
        else:
            print("No users found in database")
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
    except Exception as e:
        print(f"Error getting user: {e}")
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    
    # Add resolver_match
    try:
        request.resolver_match = resolve('/app/pos/')
        print(f"URL name: {request.resolver_match.url_name}")
    except Exception as e:
        print(f"Error resolving URL: {e}")
        class MockMatch:
            url_name = 'pos_terminal'
        request.resolver_match = MockMatch()
    
    print("\n--- Testing pos/terminal.html with tracing ---\n")
    
    # Patch Template.render
    from django.template.base import Template
    original_render = Template._render
    Template._render = patched_render
    all_templates = []
    
    try:
        sys.setrecursionlimit(500)
        html = render_to_string('pos/terminal.html', {
            'request': request,
            'products': [],
            'categories': [],
            'tables': [],
            'payment_methods': []
        })
        print(f"pos/terminal.html: OK ({len(html)} chars)")
    except RecursionError as e:
        print(f"\nRecursionError: {e}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        Template._render = original_render

if __name__ == '__main__':
    test_template()
