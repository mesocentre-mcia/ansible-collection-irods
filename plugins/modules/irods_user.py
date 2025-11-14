#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_user

short_description: configure iRODS users

description:
  - "Configures iRODS users provided in the `name` or `names` option according
     to `state`"
  - "To use this module, `become_user` must be set to a unix user configured to
     have access to a rodsadmin iRODS user."

options:
  zone:
    description: name of iRODS zone
    required: false
    type: str
    default: <local zone>
  name:
    description: name of iRODS user
    required: true
    type: str
  names:
    description: list of iRODS user names
    required: true
    type: list[str]
  state:
    description: state
    required: false
    type: str
    choices: [present, absent]
  type:
    description: user type
    required: false
    default: rodsuser
    type: str
    choices: [rodsadmin, rodsgroup, rodsuser]
  info:
    description:
      - "If `state: present', enforces `user_info` for the selected users to
         the provided value"
    required: false
    type: str
  comment:
    description:
      - "If `state: present', enforces `r_comment` for the selected users to
         the provided value"
    required: false
    type: str

author:
    - "Pierre Gay (@pigay)"
'''

EXAMPLES = r'''
- name: create some iRODS users
  mcia.irods.irods_user:
    names:
      - demoUser1
      - demoUser2
    type: rodsuser
    state: present
    info: "created with Ansible"
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsQuest,
    IrodsAdmin,
    get_zones,
)

_USER_FIELDS = [
    'USER_ID',
    'USER_NAME',
    'USER_TYPE',
    'USER_ZONE',
    'USER_INFO',
    'USER_COMMENT',
]

_USER_PARAM_FIELDS = {
    'zone': 'USER_ZONE',
    'type': 'USER_TYPE',
    'comment': 'USER_COMMENT',
    'info': 'USER_INFO',
}

_MODUSER_PARAMS = {v: k for k, v in _USER_PARAM_FIELDS.items()}

def get_users(module):
    iquest = IrodsQuest()

    fmt = ':'.join(['%s'] * len(_USER_FIELDS))

    cmd = 'select ' + ', '.join(_USER_FIELDS)
    if (module.params['zone'] is not None):
        cmd += ' where USER_ZONE = \'%s\'' % module.params['zone']

    r, o, e = module.run_command(iquest(['--no-page', fmt, cmd]))

    if r != 0:
        module.fail_json(
            msg='iquest cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )

    if 'CAT_NO_ROWS_FOUND' in o:
        return {}

    users = {}

    for l in o.strip().split('\n'):
        values = l.strip().split(':')
        user = dict(zip(_USER_FIELDS, values))
        users[user['USER_NAME']] = user

    return users

def params_to_users(params):
    skel = {}

    for k, v in _USER_PARAM_FIELDS.items():
        if params[k] is not None:
            skel[v] = params[k]
 
    if params['names'] is not None:
        names = params['names']
    elif params['name'] is not None:
        names = [params['name']]
    else:
        raise Exception("No username given (Should not happen according to module logic)")

    users = {}

    for name in names:
        u = skel.copy()
        u['USER_NAME'] = name
        users[name] = u

    return users


def users_to_string(users):
    return '\n'.join([
        ':'.join([k + '=' + v for k, v in sorted(u.items())])
        for u in users.values()
    ]) + '\n'


def delete_user(module, user):
    iadmin = IrodsAdmin()

    user_name = user['USER_NAME']
    if user['USER_TYPE'] == 'rodsgroup':
        cmd = ['rmgroup', user_name]
    else:
        if 'USER_ZONE' in user:
            user_name += '#' + user['USER_ZONE']
        cmd = ['rmuser', user_name]
    r, o, e = module.run_command(iadmin(cmd))

    if r != 0:
        module.fail_json(
            msg='iadmin cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )


def add_user(module, user):
    iadmin = IrodsAdmin()

    user_name = user['USER_NAME']
    if user['USER_TYPE'] == 'rodsgroup':
        cmd = ['mkgroup', user_name]
    else:
        if 'USER_ZONE' in user:
            user_name += '#' + user['USER_ZONE']
        cmd = ['mkuser', user_name , user['USER_TYPE']]
    r, o, e = module.run_command(iadmin(cmd))

    if r != 0:
        module.fail_json(
            msg='iadmin cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )


def modify_user(module, user, attr, value):
    iadmin = IrodsAdmin()

    cmd = ['moduser', user, _MODUSER_PARAMS[attr], value]
    r, o, e = module.run_command(iadmin(cmd))

    if r != 0:
        module.fail_json(
            msg='iadmin cmd=\'%s\' failed with code=%s error=\'%s\'' %
            (cmd, r, e)
        )

def main():
    module_args = dict(
        zone=dict(type='str', required=False),
        name=dict(type='str'),
        names=dict(type='list', elements='str'),
        state=dict(
            type='str',
            default='present',
            required=False,
            choices=['present', 'absent'],
        ),
        type=dict(type='str', default='rodsuser', required=False),
        info=dict(type='str', required=False),
        comment=dict(type='str', required=False),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        mutually_exclusive=[
            ('name', 'names'),
        ],
        required_one_of=[
            ('name', 'names'),
        ],
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

    got = get_users(module)
    wanted = params_to_users(module.params)

    # filter got users with those specified in params
    got = {k: v.copy() for k, v in got.items() if k in wanted}

    if module.params['state'] == 'absent':
        wanted = {}
    else:
        for k, v in list(wanted.items()):
            if k in got:
                # initialize sers with catalog values
                u = got[k].copy()
                # overwrite with specified parameters
                u.update(v)
                wanted[k] = u

    if got != wanted:
        result['changed'] = True

    if module._diff:
        result['diff'] = dict(
            before=users_to_string(got),
            after=users_to_string(wanted)
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    if module.params['state'] == 'absent':
        for k, v in got.items():
            delete_user(module, v)
            result['operations'].append('delete %s' % k)
    else:
        for k, v in wanted.items():
            if k in got:
                for attr, value in v.items():
                    if got[k][attr] != value:
                        modify_user(module, k, attr, value)
                        result['operations'].append(
                            'mod %s %s %s' % (k, attr, value)
                        )
            else:
                add_user(module, v)
                result['operations'].append('add %s' % k)

                for attr in ['USER_COMMENT', 'USER_INFO']:
                    if attr in v:
                        modify_user(module, k, attr, v[attr])
                        result['operations'].append(
                            'mod %s %s %s' % (k, attr, v[attr])
                        )


    module.exit_json(**result)


if __name__ == '__main__':
    main()
