#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_resc_info

short_description: gather informations about iRODS resources

description:
  - "gather informations about iRODS resources on a iRODS zone"

options:
  zone:
    description: name of iRODS zone
    required: false
    type: str

author:
    - Pierre Gay
'''

EXAMPLES = r'''
- name: get structure of iRODS resources
  mcia.irods.irods_resc_info:
    zone: demoResc
    register: output
'''

RETURN = r'''
resc_trees:
  description: list of resource root trees
  returned: success
  type: list
  elsements: dict
  contains:
    RESC_ID:
      description: resource identifier
      type: int
    RESC_LOC:
      description: resource host name
      type: str
    RESC_NAME:
      description: resource name
      type: str
    RESC_STATUS:
      description: resource status
      type: str
    RESC_TYPE_NAME:
      description: resource type
      type: str
    RESC_VAULT_PATH:
      description: resource physical path (if appropriate)
      type: str
    RESC_ZONE_NAME:
       description: resource zone
       type: str
    RESC_CONTEXT:
       description: resource context
       type: str
   children:
      description: resource children trees (if appropriate)
      type: list
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
