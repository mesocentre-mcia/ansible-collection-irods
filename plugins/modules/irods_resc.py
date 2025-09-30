#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_resc

short_description: configure iRODS resources

description:
  - "Configure iRODS resources on a iRODS zone according to provided hierarchy."
  - "Any present hierarchy will be brutally modified to conform to the one
     provided."
  - "To use this module, `become_user` must be set to a unix user configured to
     have access to a rodsadmin iRODS user."

options:
  zone:
    description: name of iRODS zone
    required: false
    type: str
  roots:
    description: list of resource trees
    required: true
    type: list
    elements: dict
    contains:
      name:
        description: resource name
        type: str
        required: true
      type:
        description: resource type
        type: str
        required: false
      loc:
        description: resource host name (if appropriate)
        type: str
        required: false
      path:
        description: resource physical path
        type: str
        required: false
      context:
        description: resource context
        type: str
        required: false
      children:
        description: list of resource children trees (if appropriate)
        type: list
        required: false

author:
    - "Pierre Gay (@pigay)"
'''

EXAMPLES = r'''
- name: Set demoZone resources
  mcia.irods.irods_resc:
    zone: demoZone
    roots:
      - name: bundleResc
      - name: demoResc
        path: /var/lib/irods/Vault
        loc: icat.example.org
        type: unixfilesystem
      - name: replResc
        type: replication
        children:
          - name: physicalResc1
            type: unixfilesystem
            loc: irods1.example.org
            path: /var/lib/irods/Vault
          - name: physicalResc2
            type: unixfilesystem
            loc: irods2.example.org
            path: /var/lib/irods/Vault
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsQuest,
    resc_trees,
    clean_hierarchy,
    params_to_hierarchy,
    dump_hierarchies,
    compare_hierarchies,
    match_hierarchies,
)


def main():
    module_args = dict(
        zone=dict(type='str', required=False),
        roots=dict(type='list', required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False
    )

    got = resc_trees(module)
    wanted = params_to_hierarchy(module.params['roots'], module.params['zone'])

    # match wildcard patterns in wanted hierarchy
    match_hierarchies(wanted, got)

    if got != wanted:
        result['changed'] = True

    if module._diff:
        result['diff'] = dict(
            before=dump_hierarchies(got),
            after=dump_hierarchies(wanted)
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    # make changes
    result['compare'] = compare_hierarchies(module, got, wanted)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
