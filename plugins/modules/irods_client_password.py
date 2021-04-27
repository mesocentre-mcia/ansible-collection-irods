#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_client_password

short_description: sets iRODS password file for a user

version_added: "1.0.0"

description: |
    Has to be used with 'become' and 'become_user' to an irods admin account

options:
    hosts:
        description: IES FQDN (defaults to user environment value if defined)
        required: false
        type: str
    port:
        description: iRODS port (defaults to user environment value if defined)
        required: false
        type: str
    zone:
        description: name of iRODS zone (defaults to user environment value if defined)
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
    - Pierre Gay
'''

EXAMPLES = r'''
mcia.irods.irods_client_password:
  zone: demoZone
  user: demoUser
  password: SecretPassword
'''

import os
from tempfile import mkstemp

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    irods_init_client,
    irods_check_client,
)


def main():
    module_args = dict(
        host=dict(type='str', required=False),
        port=dict(type='int', required=False),
        zone=dict(type='str', required=False),
        user=dict(type='str'),
        password=dict(type='str', no_log=True),
        password_file=dict(type='str', no_log=False),
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
    password_file = module.params['password_file']

    ok = irods_check_client(module, host, port, zone, user, password_file)

    if not ok:
        result['changed'] = True

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    irods_init_client(module, host, port, zone, user, password, password_file)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
