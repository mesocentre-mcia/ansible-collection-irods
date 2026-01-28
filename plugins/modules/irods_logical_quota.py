#! /usr/bin/python

#TODO
# - check if rule engine instance is configured on server_config.json
# - do not check the presence of "asq" at each loop (maybe use facts) to improve performance


DOCUMENTATION = r'''
---
module: irods_logical_quota

short_description: configure iRODS logical quotas

description:
  - "Allows to define per collection logical quota, using the plugin
     https://github.com/irods/irods_rule_engine_plugin_logical_quotas"
  - "Rule engine need to be enabled in server configuration (not done by this module)
  - "To use this module, `become_user` must be set to a unix user configured to
     have access to a rodsadmin iRODS user."
  - "feature implemented :
     logical_quotas_start_monitoring_collection
     logical_quotas_get_collection_status
     logical_quotas_set_maximum_size_in_bytes
     logical_quotas_set_maximum_number_of_data_objects"

  - "features not implemented :
     logical_quotas_count_total_number_of_data_objects
     logical_quotas_count_total_size_in_bytes
     logical_quotas_recalculate_totals
     logical_quotas_stop_monitoring_collection
     logical_quotas_unset_maximum_number_of_data_objects
     logical_quotas_unset_maximum_size_in_bytes
     logical_quotas_unset_total_number_of_data_objects
     logical_quotas_unset_total_size_in_bytes"


requirements:
    - "plugin irods_rule_engine_plugin_logical_quotas installed on iCAT server"
    - "rule engine instance configured on server configuration : irods_rule_engine_plugin-logical_quotas-instance"
    - "see official documentation : https://github.com/irods/irods_rule_engine_plugin_logical_quotas"

options:
  collection:
    description: absolute path to collection
    required: true
    type: str
    default: <none>
  files_limit:
    description: quota set the maximum number of data objects (integer passed as string)
    required: false
    type: str
    default: <none>
  bytes_limit:
    description: quota set the maximum size in bytes (integer passed as string)
    required: false
    type: str
    default: <none>
  report_only:
    description: only report collection status (consumption and current limit configuration)
    required: false
    type: bol
    default: false

author:
  - "Antoine Migeon"
'''

EXAMPLES = r'''
- name: Set quota for a_collection limit to 100 files
  mcia.irods.irods_logical_quota:
    collection: "/myzone/home/a_collection"
    files_limit: 100
  become_user: irods

- name: Set quota for a_collection limit to 1 Giga Bytes
  mcia.irods.irods_logical_quota:
    collection: "/myzone/home/a_collection"
    bytes_limit: "{{ item.bytes_limit | default('') }}"
    files_limit: "{{ item.files_limit | default('') }}"
  loop:
    - { collection: "/myzone/home/a_collection", files_limit: "99"}
    - { collection: "/myzone/home/other_collection", files_limit: "10", bytes_limit: "1073741824"}

- name: Report consumption in register quota_stats
  mcia.irods.irods_logical_quota:
    collection: "{{ item.collection }}"
    report_only: True
  register: quota_stats
  loop:
    - { collection: "/myzone/home/a_collection"}
    - { collection: "/myzone/home/other_collection"}

'''

RETURN = r'''
# Always return collection status (current consumption and configured limits) even if only asked to set a limit
collection:
    description: the collection target path
    type: str
    returned: always
    sample: "/myzone/home/a_collection"
total_bytes:
    description: the current bytes consumption
    type: str
    returned: always
    sample: {"total_bytes": "4253942311"}
total_files:
    description: the current number of object consumption
    type: str
    returned: always
    sample: {"total_files": "19"}
bytes_limit:
    description: the bytes limit configured
    type: str
    returned: always
    sample: {"bytes_limit": "20000"}
files_limit:
    description: the files limit configured
    type: str
    returned: always
    sample: {"files_limit": "10123200"}
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.mcia.irods.plugins.module_utils.irods_utils import (
    IrodsQuest,
    IrodsLs,
    IrodsRule,
    IrodsAdmin
)

import json

_QUOTA_FIELDS = {
    'bytes_limit' : 'irods::logical_quotas::maximum_size_in_bytes',
    'files_limit' : 'irods::logical_quotas::maximum_number_of_data_objects',
    'total_bytes' : 'irods::logical_quotas::total_size_in_bytes',
    'total_files' : 'irods::logical_quotas::total_number_of_data_objects',
}

# required to enable logical quota monitoring
def add_specific_query_logical_quotas(module):

    iadmin = IrodsAdmin()
    iquest = IrodsQuest()

    specific_queries = {
            "logical_quotas_count_data_objects_recursive" : "select count(distinct data_id) from R_DATA_MAIN d inner join R_COLL_MAIN c on d.coll_id = c.coll_id where coll_name like ?",
            "logical_quotas_sum_data_object_sizes_recursive" : "select sum(t.data_size) from (select data_id, data_size from R_DATA_MAIN d inner join R_COLL_MAIN c on d.coll_id = c.coll_id where coll_name like ? and data_is_dirty in (\'1\', \'4\') group by data_id, data_size) as t"
    }

    for specific_query in specific_queries:

        # check if queries are already configured
        cmd = ['--no-page', '--sql', 'lsl', specific_queries[specific_query] ]
        r, o, e = module.run_command(iquest(cmd))

        if r != 0:
            module.fail_json(
                msg='iquest cmd=\'%s\' failed with code=%s error=\'%s\'' %
                (cmd, r, e)
            )

        if 'CAT_NO_ROWS_FOUND' in o:
            # add query if necessery
            cmd = ['asq', specific_query]
            r, o, e = module.run_command(iadmin(cmd))

            if r != 0:
                module.fail_json(
                    msg='iadmin cmd=\'%s\' failed with code=%s error=\'%s\'' %
                    (cmd, r, e)
                )


def invoke_rule(module, rule):

    irule = IrodsRule()

    cmd = ['-r', 'irods_rule_engine_plugin-logical_quotas-instance', json.dumps(rule), 'null', 'ruleExecOut']
    r, o, e = module.run_command(irule(cmd))

    if r != 0:
        # check mode can fail here if monitoring not stared
        if module.check_mode:
            return "{}"
        else:
            module.fail_json(
                msg='irule cmd=\'%s\' failed with code=%s error=\'%s\'' %
                (cmd, r, e)
            )

    return o


def main():
    rule = {}
    module_args = dict(
        collection=dict(type='str', required=True),
        bytes_limit=dict(type='str', required=False),
        files_limit=dict(type='str', required=False),
        report_only=dict(type='bool', required=False, default=False)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
        collection=module.params['collection']
    )

    # check if collection exist
    ils = IrodsLs()
    r, o, e = module.run_command(ils([module.params['collection']]))
    if r != 0:
        module.fail_json(msg='collection \'%s\' not found with code=%s error=\'%s\'' % (module.params['collection'], r, e))


    # add initial engine configuration
    if not module.params['report_only'] and module.check_mode is not True:
        add_specific_query_logical_quotas(module) 

    # start monitoring (even in report_only otherwise get_collection_status fails)
    if module.check_mode is not True:
        rule['operation'] = 'logical_quotas_start_monitoring_collection'
        rule['collection'] = module.params['collection']
        invoke_rule(module, rule)


    # get initial collection status
    rule['operation']='logical_quotas_get_collection_status'
    rule['collection']=module.params['collection']
    rule_output = invoke_rule(module, rule)
    initial_collection_status = json.loads(invoke_rule(module, rule))
    # store result status
    for k, v in _QUOTA_FIELDS.items():
        if v in initial_collection_status:
            result[k] = initial_collection_status[v]
        else:
            result[k] = ""
#    result['bytes_limit'] = initial_collection_status['irods::logical_quotas::maximum_size_in_bytes']
#    result['files_limit'] = initial_collection_status['irods::logical_quotas::maximum_number_of_data_objects']
#    result['total_bytes'] = initial_collection_status['irods::logical_quotas::total_size_in_bytes']
#    result['total_files'] = initial_collection_status['irods::logical_quotas::total_number_of_data_objects']

    if (result['bytes_limit'] != module.params['bytes_limit']) or (result['files_limit'] != module.params['files_limit']):
        result['diff'] = dict(
            before=dict(
                bytes_limit=result['bytes_limit'],
                files_limit=result['files_limit']),
            after=dict(
                bytes_limit=module.params['bytes_limit'],
                files_limit=module.params['files_limit'])
        )
        if not module.params['report_only']:
            result['changed'] = True

    if not module.check_mode and not module.params['report_only']:
        # set quota max size
        if module.params['bytes_limit'] and module.params['bytes_limit'] != result['bytes_limit']:
            rule['operation'] = 'logical_quotas_set_maximum_size_in_bytes'
            rule['collection'] = module.params['collection']
            rule['value'] = module.params['bytes_limit']
            invoke_rule(module, rule)
            result['bytes_limit'] = module.params['bytes_limit']
            result['changed'] = True

        # set quota max files
        if module.params['files_limit'] and module.params['files_limit'] != result['files_limit']:
            rule['operation'] = 'logical_quotas_set_maximum_number_of_data_objects'
            rule['collection'] = module.params['collection']
            rule['value'] = module.params['files_limit']
            invoke_rule(module, rule)
            result['files_limit'] = module.params['files_limit']
            result['changed'] = True


    module.exit_json(**result)


if __name__ == '__main__':
    main()
