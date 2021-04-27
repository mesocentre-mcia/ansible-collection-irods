
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os.path
from fnmatch import fnmatch


# iRODS resource hierarchy description fields
_RESC_HIERARCHY_FIELDS = [
    'RESC_ID',
    'RESC_PARENT',
]


# iRODS resource description fields
_RESC_MANDATORY_FIELDS = [
    'RESC_NAME',
    'RESC_ZONE_NAME', # can be set with a default value
]


# iRODS fields that can be skipped or wildcarded in ansible description
_RESC_OPTIONAL_FIELDS = [
    'RESC_TYPE_NAME',
    'RESC_LOC',
    'RESC_VAULT_PATH',
    'RESC_STATUS',
    'RESC_COMMENT',
    'RESC_INFO',
    'RESC_CONTEXT',
]


_RESC_FIELDS = (
    _RESC_HIERARCHY_FIELDS +
    _RESC_MANDATORY_FIELDS +
    _RESC_OPTIONAL_FIELDS
)


_MODRESC_ATTR_NAME = {
#    'RESC_TYPE_NAME': 'type',
    'RESC_LOC': 'host',
    'RESC_VAULT_PATH': 'path',
    'RESC_STATUS': 'status',
    'RESC_COMMENT': 'comment',
    'RESC_INFO': 'info',
    'RESC_CONTEXT': 'context',
}


_ZONE_FIELDS = [
    'ZONE_NAME',
    'ZONE_TYPE',
    'ZONE_CONNECTION',
    'ZONE_COMMENT',
]


class IrodsCommand:

    def __init__(self, cmd_prefix=''):
        self.cmd_prefix = cmd_prefix

    def _command(self):
        raise NotImplementedError

    def _command_path(self):
        command = self._command()
        if self.cmd_prefix:
            command = os.path.join(self.cmd_prefix, 'bin', command)
        return command

    def __call__(self, cmdline):
        env = {}

        if self.cmd_prefix:
            env['LD_LIBRARY_PATH'] = os.path.join(self.cmd_prefix, 'lib')

        return [self._command_path()] + cmdline


class IrodsAdmin(IrodsCommand):

    def _command(self):
        return 'iadmin'


class IrodsQuest(IrodsCommand):

    def _command(self):
        return 'iquest'


class IrodsEnv(IrodsCommand):

    def _command(self):
        return 'ienv'


class IrodsInit(IrodsCommand):

    def _command(self):
        return 'iinit'


def ienv(module):
    ienv = IrodsEnv()

    r, o, e = module.run_command(ienv([]))

    if r != 0:
        module.fail_json(
            msg='ienv command failed with code=%s error=\'%s\'' %
            (r, e)
        )

    ret = {}

    for l in o.strip().split('\n'):
        k, v = l.strip().split(' - ', 1)
        ret[k] = v

    return ret


def get_zones(module, **args):
    iquest = IrodsQuest()

    fmt = ':'.join(['%s'] * len(_ZONE_FIELDS))

    cmd = 'select ' + ', '.join(_ZONE_FIELDS)
    where_clauses = ['%s = \'%s\'' % a for a in args.items()]
    if where_clauses:
        cmd += ' where ' + ' and '.join(where_clauses)

    r, o, e = module.run_command(iquest(['--no-page', fmt, cmd]))

    if r != 0:
        module.fail_json(
            msg='iquest cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )

    ret = []
    for l in o.strip().split('\n'):
        values = l.strip().split(':')
        zone = dict(zip(_ZONE_FIELDS, values))
        ret.append(zone)

    return ret


def resc_trees(module):
    iquest = IrodsQuest()

    fmt = ':'.join(['%s'] * len(_RESC_FIELDS))

    cmd = 'select ' + ', '.join(_RESC_FIELDS)
    if (module.params['zone'] is not None):
        cmd += ' where RESC_ZONE_NAME = \'%s\'' % module.params['zone']

    r, o, e = module.run_command(iquest(['--no-page', fmt, cmd]))

    if r != 0:
        module.fail_json(
            msg='iquest cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )

    # build a resc dict and a list of root resc
    rescs = {}
    roots = set()
    for l in o.strip().split('\n'):
        values = l.strip().split(':')
        resc = dict(zip(_RESC_FIELDS, values))

        # fields can't be deleted or set to empty string
        # we emulate this with blank string
        for k in _RESC_OPTIONAL_FIELDS:
            if k in resc and resc[k].strip() == '':
                resc[k] = ''

        resc['children'] = []

        resc['RESC_ID'] = int(resc['RESC_ID'])

        if resc['RESC_LOC'] == 'EMPTY_RESC_HOST':
            resc['RESC_LOC'] = None

        if resc['RESC_VAULT_PATH'] == 'EMPTY_RESC_PATH':
            resc['RESC_VAULT_PATH'] = None

        if resc['RESC_PARENT'] == '':
            resc['RESC_PARENT'] = None
        else:
            resc['RESC_PARENT'] = int(resc['RESC_PARENT'])

        rescs[resc['RESC_ID']] = resc

    # build resc trees
    for r in list(rescs.values()):

        p_rid = r['RESC_PARENT']

        if p_rid is None:
            roots.add(r['RESC_ID'])
            continue

        parent = rescs[p_rid]
        parent['children'].append(r)
        r['RESC_PARENT'] = parent['RESC_NAME']

    for r in list(rescs.values()):
        clean_hierarchy(r)

    return sorted([rescs[rid] for rid in roots], key=lambda r: r['RESC_NAME'])


def clean_hierarchy(h):
    for k in ['RESC_ID']:
        if k in h:
            del h[k]

    for k in ['RESC_LOC', 'RESC_VAULT_PATH']:
        if k in h and h[k] is None:
            del h[k]

    if 'children' in h:
        if h['children'] in ([], None):
            del h['children']
        else:
            for c in h['children']:
                clean_hierarchy(c)

            h['children'] = sorted(h['children'], key=lambda c: c['RESC_NAME'])


def param_to_resc(param, default_zone):
    r = {
        # _RESC_MANDATORY_FIELDS
        'RESC_NAME': param['name'],
        'RESC_ZONE_NAME': param.get('zone', default_zone),

        # _RESC_OPTIONAL_FIELDS
        'RESC_TYPE_NAME': param.get('type', '*'),
        'RESC_LOC': param.get('loc', None),
        'RESC_VAULT_PATH': param.get('path', None),
        'RESC_STATUS': param.get('status', '*'),
        'RESC_COMMENT': param.get('comment', '*'),
        'RESC_INFO': param.get('info', '*'),
        'RESC_CONTEXT': param.get('context', '*'),


        # hierarchy
        'children': [],
        'RESC_PARENT': None,
    }

    if 'children' in param:
        for pc in param['children']:
            c = param_to_resc(pc, default_zone)
            r['children'].append(c)
            c['RESC_PARENT'] = r['RESC_NAME']

    return r


def params_to_hierarchy(params_roots, default_zone):
    roots = []

    # FIXME: avoid multiple resources with identical names
    for pr in params_roots:
        r = param_to_resc(pr, default_zone)
        clean_hierarchy(r)
        roots.append(r)

    return sorted(roots, key=lambda c: c['RESC_NAME'])


def match_hierarchy(match, reference_dict):
    if match['RESC_NAME'] in reference_dict:
        # compare match and reference resources
        reference = reference_dict[match['RESC_NAME']]

        for field in _RESC_OPTIONAL_FIELDS:
            if field not in match:
                if field in reference:
                    match[field] = reference[field]

                continue

            ref_field = reference.get(field, '')
            if fnmatch(ref_field, match[field]):
                match[field] = ref_field
    else:
        # RESC_NAME not found in reference_dict, remove wildcards
        for field in _RESC_OPTIONAL_FIELDS:
            if field not in match:
                continue

            if not (set(match[field]) - set('*?')):
                # match[field] is a wildcard only field, remove it
                del match[field]

    if 'children' in match:
        for c in match['children']:
            match_hierarchy(c, reference_dict)


def match_hierarchies(matchs, references):
    def resc_dict(hier):
        ret = {hier['RESC_NAME']: hier}

        for c in hier.get('children', []):
            ret.update(resc_dict(c))

        return ret

    def resc_dicts(hier_list):
        ret = {}
        for h in hier_list:
            ret.update(resc_dict(h))

        return ret

    reference_dict = resc_dicts(references)

    for match in matchs:
        match_hierarchy(match, reference_dict)

def dump_hierarchy(hier, offest='  '):
    ret = ':'.join([str(hier.get(k, '')) for k in _RESC_FIELDS]) + '\n'

    if 'children' not in hier:
        return ret

    for child in hier['children']:
        ret += offest + dump_hierarchy(child, offest + '  ') + '\n'

    return ret

def dump_hierarchies(hier_list):
    ret = ''
    for hier in hier_list:
        ret += dump_hierarchy(hier)

    return ret


def compare_hierarchies(module, from_list, to_list):
    def resc_key(resc):
        '''Build a tuple to be used as a resc unique key from meaningful fields
        '''
        return tuple(resc.get(k, None) for k in [
            'RESC_NAME',
            'RESC_ZONE_NAME',
            'RESC_TYPE_NAME',
            'RESC_LOC',
        ])

    def resc_dict(hier):
        ret = {resc_key(hier): hier}

        for c in hier.get('children', []):
            ret.update(resc_dict(c))

        return ret

    def resc_dicts(hier_list):
        ret = {}
        for h in hier_list:
            ret.update(resc_dict(h))

        return ret

    def _run(args):
        r, o, e = module.run_command(args)

        if r != 0:
            module.fail_json(
                msg='iquest cmd=\'%s\' failed with code=%s error=\'%s\'' %
                (' '.join(args), r, e)
            )

        return o

    # build dicts with all resources for each side
    all_from = resc_dicts(from_list)
    all_to = resc_dicts(to_list)

    # build sets of resc keys for each side
    from_set = set(all_from.keys())
    to_set = set(all_to.keys())

    # lists of resources for each operation needed
    rmresc = [all_from[k] for k in from_set - to_set]
    mkresc = [all_to[k] for k in to_set - from_set]
    rmchild = []
    addchild = []
    modresc = []

    for k in from_set & to_set:
        f = all_from[k]
        t = all_to[k]

        if f['RESC_PARENT'] != t['RESC_PARENT']:
            if f['RESC_PARENT'] is not None:
                rmchild.append(f)
            if t['RESC_PARENT'] is not None:
                addchild.append(t)

        for field in _RESC_OPTIONAL_FIELDS:
            if field in f and (field not in t or t[field] != f[field]):
                modresc.append((t['RESC_NAME'], field, t[field]))

    iadmin = IrodsAdmin()
    operations = []

    # break parent-child relationships
    for child in rmchild:
        op = ['rmchildfromresc', child['RESC_PARENT'], child['RESC_NAME']]
        operations.append(iadmin(op))

    # iadmin rmresc must be run on root resources
    for rm in rmresc:
        if rm['RESC_PARENT'] is not None:
            op = ['rmchildfromresc', rm['RESC_PARENT'], rm['RESC_NAME']]
            operations.append(iadmin(op))

    # delete resources
    for rm in rmresc:
        op = ['rmresc', rm['RESC_NAME']]
        operations.append(iadmin(op))

    # add resources
    for mk in mkresc:
        op = [
            'mkresc',
            mk['RESC_NAME'],
            mk['RESC_TYPE_NAME'],
        ]
        if 'RESC_LOC' in mk:
            op.append(':'.join([mk['RESC_LOC'], mk['RESC_VAULT_PATH']]))
        elif 'RESC_CONTEXT' in mk:
            op.append('""')

        if 'RESC_CONTEXT' in mk:
            op.append(mk['RESC_CONTEXT'])

        operations.append(iadmin(op))

        # set configured fields for new resource
        for attr in ['RESC_STATUS', 'RESC_COMMENT', 'RESC_INFO']:
            if attr not in mk:
                continue

            op = [
                'modresc',
                mk['RESC_NAME'],
                _MODRESC_ATTR_NAME[attr],
                mk[attr]
            ]

            operations.append(iadmin(op))

    # add parent-child relationship to new resources
    for mk in mkresc:
        if mk['RESC_PARENT'] is not None:
            op = ['addchildtoresc', mk['RESC_PARENT'], mk['RESC_NAME']]

            operations.append(iadmin(op))

    # add parent-child relationship to old resources
    for child in addchild:
        # TODO: implement context for parent-child relationship
        op = ['addchildtoresc', child['RESC_PARENT'], child['RESC_NAME']]

        operations.append(iadmin(op))

    # modify resources
    for name, attr, value in modresc:
        attr = _MODRESC_ATTR_NAME[attr]
        if value in ['', None]:
            # iadmin modresc doesn't support empty value strings
            # use space ' ' instead
            value = ' '
        op = ['modresc', name, attr, value]

        operations.append(iadmin(op))

    # run operations
    for op in operations:
        _run(op)

    return [' '.join(op) for op in operations]
