#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_user_quota

short_description: configure iRODS users quotas

version_added: "1.0.0"

description: |
    Has to be used with 'become' and 'become_user'

options:
    zone:
        description: name of iRODS zone (defaults to local zone)
        required: false
        type: str
    limits:
        description: dictionary of limit per user
        required: true
        type: dict(int)
    resource:
        description: name of resource (defaults to 'total')
        required: false
        type: str

author:
    - Pierre Gay
'''

EXAMPLES = r'''
mcia.irods.irods_user:
  zone: demoZone
  resource: demoResc
  limits:
    demoUser: 10000
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsQuest,
    IrodsAdmin,
    get_zones,
    rescs_id_name,
)

_QUOTA_FIELDS = [
    'QUOTA_USER_NAME',
    'QUOTA_USER_ZONE',
    'QUOTA_RESC_ID',
    'QUOTA_LIMIT',
]

_QUOTA_PARAM_FIELDS = {
    'zone': 'QUOTA_USER_ZONE',
    'limits': 'QUOTA_USER_NAME',
    'resource': 'QUOTA_RESC_ID',
}


def get_quotas(module):

    # get resc names from their id
    rescs = rescs_id_name(module)
    rescs[0] = 'total'

    iquest = IrodsQuest()

    fmt = ':'.join(['%s'] * len(_QUOTA_FIELDS))

    where = ['QUOTA_USER_TYPE <> \'rodsgroup\'']

    if (module.params['zone'] is not None):
        where += 'QUOTA_USER_ZONE = \'%s\'' % module.params['zone']

    cmd = 'select {} where {}'.format(
        ', '.join(_QUOTA_FIELDS),
        'and'.join(where)
    )

    r, o, e = module.run_command(iquest(['--no-page', fmt, cmd]))

    if r != 0:
        module.fail_json(
            msg='iquest cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )

    if 'CAT_NO_ROWS_FOUND' in o:
        return {}

    quotas = {}

    for l in o.strip().split('\n'):
        values = l.strip().split(':')
        quota = dict(zip(_QUOTA_FIELDS, values))

        # translate resc id to name
        quota['QUOTA_RESC_ID'] = rescs[int(quota['QUOTA_RESC_ID'])]

        # convrt limit to int
        quota['QUOTA_LIMIT'] = int(quota['QUOTA_LIMIT'])

        quotas[quota['QUOTA_USER_NAME']] = quota

    return quotas



def params_to_quotas(params):
    skel = {}

    for k, v in _QUOTA_PARAM_FIELDS.items():
        if params[k] is not None:
            skel[v] = params[k]

    quotas = {}

    for user, limit in params['limits'].items():
        u = skel.copy()
        u['QUOTA_USER_NAME'] = user
        u['QUOTA_LIMIT'] = limit
        quotas[user] = u

    return quotas

def qprint(q):
    return ' '.join([
        'iadmin',
        'suq',
        q['QUOTA_USER_NAME'] + '#' + q['QUOTA_USER_ZONE'],
        q['QUOTA_RESC_ID'],
        str(q['QUOTA_LIMIT']),
    ])

def quotas_to_string(quotas):

    return '\n'.join([qprint(v) for v in quotas.values()]) + '\n'

def set_user_quota(module, user, zone, resource, limit):
    iadmin = IrodsAdmin()

    cmd = ['suq', user + '#' + zone, resource, str(limit)]
    r, o, e = module.run_command(iadmin(cmd))

    if r != 0:
        module.fail_json(
            msg='iadmin cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )

def main():
    module_args = dict(
        zone=dict(type='str', required=False),
        limits=dict(
            type='dict',
        ),
        resource=dict(type='str', default='total')
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
        operations=[],
    )

    # we need a zone to ensure we get unique users
    if module.params['zone'] is None:
        # default to local zone (must be only one)
        local_zone = get_zones(module, ZONE_TYPE='local')[0]
        module.params['zone'] = local_zone['ZONE_NAME']


    got = get_quotas(module)
    wanted = params_to_quotas(module.params)

    # filter got users with those specified in params
    got = {k: v.copy() for k, v in got.items() if k in wanted}

    if got != wanted:
        result['changed'] = True

    if module._diff:
        result['diff'] = dict(
            before=quotas_to_string(got),
            after=quotas_to_string(wanted)
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    for k, v in got.items():
        w = wanted[k]
        if v != w:
            result['operations'].append(qprint(w))
            set_user_quota(module,
                           w['QUOTA_USER_NAME'],
                           w['QUOTA_USER_ZONE'],
                           w['QUOTA_RESC_ID'],
                           w['QUOTA_LIMIT'])

    module.exit_json(**result)


if __name__ == '__main__':
    main()
