#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_user_quota

short_description: configure iRODS users quotas

description:
  - "Allows to define per zone and per resource user quotas. Identical quota can
     be set for group members by specifying `'%group_name': limit`."
  - "User limit takes precedence upon group limit. Precedence between group
     limits is undefined."
  - "To use this module, `become_user` must be set to a unix user configured to
     have access to a rodsadmin iRODS user."

options:
  zone:
    description: name of iRODS zone
    required: false
    type: str
    default: <local zone>
  limits:
    description: dictionary of limit per user/group
    required: true
    type: dict(int)
  resource:
    description: name of resource
    required: false
    type: str
    default: "total"

author:
  - "Pierre Gay (@pigay)"
'''

EXAMPLES = r'''
- name: Set quota for demoUser
  mcia.irods.irods_user:
    zone: demoZone
    resource: demoResc
    limits:
      demoUser: 10000

- name: Set identical quota for all users in group demoGroup except demoUser
  mcia.irods.irods_user:
    zone: demoZone
    resource: demoResc
    limits:
      '%demoGroup': 20000
      demoUser: 30000
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsQuest,
    IrodsAdmin,
    get_zones,
    rescs_id_name,
    get_user_groups,
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
        where += ['QUOTA_USER_ZONE = \'%s\'' % module.params['zone']]

    cmd = 'select {} where {}'.format(
        ', '.join(_QUOTA_FIELDS),
        ' and '.join(where)
    )

    r, o, e = module.run_command(iquest(['--no-page', fmt, cmd]))

    if (r!= 1 and r != 0) or (r==1 and 'CAT_NO_ROWS_FOUND' not in o):
        module.fail_json(
            msg='iquest fmt=\'%s\' cmd=\'%s\' failed with code=%s output=\'%s\' error=\'%s\'' %
            (fmt, cmd, r, o, e)
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
    group_quotas = {}

    for user, limit in params['limits'].items():
        qdict = quotas
        if user.startswith('%'):
            user = user[1:]
            qdict = group_quotas

        u = skel.copy()

        u['QUOTA_USER_NAME'] = user
        u['QUOTA_LIMIT'] = limit

        qdict[user] = u

    return quotas, group_quotas

def qprint(q, type):
    return ' '.join([
        'iadmin',
        f's{type}q',
        q['QUOTA_USER_NAME'] + '#' + q['QUOTA_USER_ZONE'],
        q['QUOTA_RESC_ID'],
        str(q['QUOTA_LIMIT']),
    ])

def quotas_to_string(quotas, type):

    return '\n'.join([qprint(quotas[k], type) for k in sorted(quotas.keys())]) + '\n'


def set_quota(module, type, user, zone, resource, limit):
    iadmin = IrodsAdmin()

    cmd = [f's{type}q', user + '#' + zone, resource, str(limit)]
    r, o, e = module.run_command(iadmin(cmd))
    module.warn(f'set_quota {cmd}')

    if r != 0:
        module.fail_json(
            msg='iadmin cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )


def set_user_quota(module, user, zone, resource, limit):
    return set_quota(module, 'u', user, zone, resource, limit)


def set_group_quota(module, user, zone, resource, limit):
    return set_quota(module, 'g', user, zone, resource, limit)


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

    user_quotas, group_quotas = params_to_quotas(module.params)

    user_groups = get_user_groups(module, module.params['zone'])


    # for g, q in group_quotas.items():
    #     for u in user_groups[g]:
    #         if u not in user_quotas:
    #             user_quotas[u] = got[u].copy()
    #             user_quotas[u]['QUOTA_LIMIT'] = q['QUOTA_LIMIT']

    # filter got users with those specified in params
    got_users = {k: v.copy() for k, v in got.items() if k in user_quotas}
    got_groups = {k: v.copy() for k, v in got.items() if k in group_quotas}


    if got_users != user_quotas | got_groups !=group_quotas:
        result['changed'] = True

    if module._diff:
        result['diff'] = dict(
            before=(quotas_to_string(got_users, 'u') + quotas_to_string(got_groups, 'g')).strip(),
            after=(quotas_to_string(user_quotas, 'u') + quotas_to_string(group_quotas, 'g')).strip()
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    for k, v in user_quotas.items():
        w = got_users[k]
        if v != w:
            result['operations'].append(qprint(v, 'u'))
            set_user_quota(module,
                           v['QUOTA_USER_NAME'],
                           v['QUOTA_USER_ZONE'],
                           v['QUOTA_RESC_ID'],
                           v['QUOTA_LIMIT'])
            

    for k, v in group_quotas.items():
        w = got_groups[k]
        if v != w:
            result['operations'].append(qprint(v, 'g'))
            set_group_quota(module,
                           v['QUOTA_USER_NAME'],
                           v['QUOTA_USER_ZONE'],
                           v['QUOTA_RESC_ID'],
                           v['QUOTA_LIMIT'])

    module.exit_json(**result)


if __name__ == '__main__':
    main()
