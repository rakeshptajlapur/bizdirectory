from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    
@register.filter
def make_list(value):
    """Convert a string to a list of characters"""
    return list(value)

@register.filter
def get_item(dictionary_list, key):
    """
    Gets an item from a list of dictionaries based on a key
    Used for getting business hours by weekday
    """
    for item in dictionary_list:
        if item.day == key:
            return item
    return None