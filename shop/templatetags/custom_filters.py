import locale
from django import template

register = template.Library()

locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')

@register.filter
def currency(value):
    try:
        value = float(value)
        return locale.format_string("%d", value, grouping=True) + '₫'
    except (ValueError, TypeError):
        return value
