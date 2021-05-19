
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


from ansible.errors import AnsibleFilterError


def filter_resc(resc_trees, **attr_dict):
    '''
    Filters resource tree list according to provided keyword arguments.

    Each keyword argument name has to be a resource attribute (name, type, loc,
    path). Keyword argument value can be a string or list of strings.

    Each individual resource in resc_trees will be checked for attribute value
    matching each of the keyword arguments value. For keyword arguments will
    list values, a resource will match if its attribute matches any of the list
    values.
    '''
    for k, v in list(attr_dict.items()):
        if isinstance(v, str):
            attr_dict[k] = [v]

    if isinstance(resc_trees, dict):
        return filter_resc([resc_trees], **attr_dict)

    if not isinstance(resc_trees, list):
        raise AnsibleFilterError('the resc_trees must be a dictionary or a list')

    ret = []

    for t in resc_trees:
        ok = True
        for k, v in attr_dict.items():
            if not (k in t and t[k] in v):
                ok = False
                break
        if ok:
            ret.append(t)

        if 'children' in t:
            ret += filter_resc(t['children'], **attr_dict)

    return ret


# ---- Ansible filters ----
class FilterModule(object):
    ''' iRODS resources filters '''

    def filters(self):
        return {
            'filter_resc': filter_resc,
        }
