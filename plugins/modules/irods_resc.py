#! /usr/bin/python


DOCUMENTATION = r'''
---
module: irods_resc

short_description: configure iRODS resources

version_added: "1.0.0"

description: configure iRODS resources on a iRODS zone according to provided
             hierarchy

options:
    zone:
        description: name of iRODS zone
        required: false
        type: str

author:
    - Pierre Gay
'''

EXAMPLES = r'''
mcia.irods.irods_resc:
  zone: demoResc
  roots:
    - name: demoResc
      path: /var/lib/irods/Vault
      loc: icat.example.org
      type: unixfilesystem
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

    # TODO: make changes

    result['compare'] = compare_hierarchies(module, got, wanted)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
