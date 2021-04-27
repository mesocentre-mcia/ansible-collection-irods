#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_user_password

short_description: sets iRODS password for an user

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
mcia.irods.irods_user_password:
  zone: demoZone
  name: demoUser
  password: SecretPassword
'''

import os
from tempfile import mkstemp

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsAdmin,
    IrodsInit,
)


def irods_env(host, port, zone):
   env = {}

   if host is not None:
       env['IRODS_HOST'] = host

   if port is not None:
       env['IRODS_PORT'] = str(port)

   if zone is not None:
       env['IRODS_ZONE_NAME'] = zone

   return env


CAT_INVALID_AUTHENTICATION = 7


def check_irods_password(module, host, port, zone, user, password):
    fd, pwdfile = mkstemp()
    try:
        os.close(fd)

        env = dict(
            IRODS_USER_NAME=user,
            IRODS_AUTHENTICATION_FILE=pwdfile,
        )

        env.update(irods_env(host, port, zone))

        iinit = IrodsInit()

        r, o, e = module.run_command(iinit([password]), environ_update=env)

        if r == CAT_INVALID_AUTHENTICATION:
            return False

        if r != 0:
            module.fail_json(
                msg='iinit failed with code=%s error=\'%s\'' %
                    (r, e)
            )

        return True

    finally:
        os.unlink(pwdfile)

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
