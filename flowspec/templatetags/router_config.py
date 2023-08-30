from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

register = template.Library()

@register.filter
def exawrap(qset, field):
    '''
    Filter for flowspec config that returns:
    emptystring if qset has no elements
    Contents of the specified field if it has one element
    A string of the form '[ a, b, ..., z ]' if it has multiple elements
    '''
    if qset.count() == 0:
        return ''
    elif qset.count() == 1:
        return getattr( qset.first(), field )
    else:
        return '[ ' + ', '.join([getattr(q, field) for q in qset.all()]) + ' ]'

@register.filter
def exabound(value):
    '''
    Filter for flowspec config that process a number of pair of numbers. Returns:
    emptystring if value is empty
    =value if it does not contain '-'
    A string of the form '>=(left side)&<=(right side)' if it contains '-'
    '''
    if not value:
        return ''
    elif not '-' in value:
        return '=' + value
    else:
        bound = value.split('-')
        return mark_safe(f'>={conditional_escape(bound[0])}&<={conditional_escape(bound[1])}')
