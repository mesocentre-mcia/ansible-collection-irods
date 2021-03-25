#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_resc_info

short_description: gather informations about iRODS resources

version_added: "1.0.0"

description: gather informations about iRODS resources on a iRODS zone

options:
    zone:
        description: name of iRODS zone
        required: false
        type: str

author:
    - Pierre Gay
'''

EXAMPLES = r'''
mcia.irods.irods_resc_info:
  zone: demoResc
  register: output
'''

RETURN = r'''
resc_trees:
  - RESC_ID: 10014,
    RESC_LOC: "icat.example.org"
    RESC_NAME: "demoResc"
    RESC_STATUS: ""
    RESC_TYPE_NAME: "unixfilesystem"
    RESC_VAULT_PATH: "/var/lib/irods/Vault"
    RESC_ZONE_NAME: "demoZone"
    children: []
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsQuest, resc_trees
)


def main():
    module_args = dict(
        zone=dict(type='str', required=False),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
        resc_trees=resc_trees(module)
    )

    module.exit_json(**result)


if __name__ == '__main__':
    main()
