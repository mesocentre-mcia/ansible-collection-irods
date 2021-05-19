#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_user_password

short_description: sets iRODS password for a user

description:
  - "Modifies specified user's password in the catalog"
  - "To use this module, `become_user` must be set to a unix user configured to
     have access to a rodsadmin iRODS user."

options:
  host:
    description: IES FQDN (defaults to user environment value if defined)
    required: false
    type: str
  port:
    description: iRODS port (defaults to user environment value if defined)
    required: false
    type: str
  zone:
    description:
      - "name of iRODS zone (defaults to user environment value if defined)"
    required: false
    type: str
  user:
    description: name of iRODS user
    required: true
    type: str
  password:
    description: iRODS password
    required: true
    type: str

author:
  - "Pierre Gay (@pigay)"
'''

EXAMPLES = r'''
- name: Set iRODS password for demoUser
  mcia.irods.irods_user_password:
    zone: demoZone
    user: demoUser
    password: SecretPassword
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsAdmin,
    check_irods_password,
    irods_env,
)


def change_irods_password(module, host, port, zone, user, password):
    env = irods_env(host, port, zone)

    iadmin = IrodsAdmin()

    r, o, e = module.run_command(iadmin(['moduser', user, 'password', password]))

    if r != 0:
        module.fail_json(
            msg='iadmin failed with code=%s error=\'%s\'' %
                (r, e)
        )


def main():
    module_args = dict(
        host=dict(type='str', required=False),
        port=dict(type='int', required=False),
        zone=dict(type='str', required=False),
        user=dict(type='str'),
        password=dict(type='str', no_log=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
        operations=[],
    )

    host = module.params['host']
    port = module.params['port']
    zone = module.params['zone']
    user = module.params['user']
    password = module.params['password']

    ok = check_irods_password(module, host, port, zone, user, password)

    if not ok:
        result['changed'] = True

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    change_irods_password(module, host, port, zone, user, password)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
