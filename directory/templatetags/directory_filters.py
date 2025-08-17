# directory/templatetags/directory_filters.py
from django import template

register = template.Library()

@register.filter
def filter_by_category(businesses, category_id):
    """Filter businesses by category ID"""
    return businesses.filter(category_id=category_id)

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary and key in dictionary:
        return dictionary[key]
    return None