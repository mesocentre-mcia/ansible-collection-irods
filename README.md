# Ansible iRODS Collection

Provides modules and roles for [iRODS](http://irods.org/) operations.

## Tested with Ansible

Tested with Ansible 2.9 and 2.10.

## External requirements

The exact requirements for every module or role are listed in the module/role
documentation.

## Included Content

* Modules:
  * irods_client_password
  * irods_resc_info
  * irods_resc
  * irods_user_password
  * irods_user_quota
  * irods_user

* Filters:
  * filter_resc

* Roles:
  * irods

## Using this collection

Before using mcia.irods collection, you need to install the collection with the
`ansible-galaxy` CLI.

    ansible-galaxy collection install mcia.irods

You can also include it in a `requirements.yml` file and install it via
`ansible-galaxy collection install -r requirements.yml` using the format:

```yaml
collections:
- name: mcia.irods
```

See [Ansible Using collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html) for more details.

## Contributing to this collection

<!--Describe how the community can contribute to your collection. At a minimum,
include how and where users can create issues to report problems or request
features for this collection.  List contribution requirements, including
preferred workflows and necessary testing, so you can benefit from community
PRs. If you are following general Ansible contributor guidelines, you can link
to - [Ansible Community Guide](https://docs.ansible.com/ansible/latest/community/index.html).
-->

We're following the general Ansible contributor guidelines; see [Ansible Community Guide](https://docs.ansible.com/ansible/latest/community/index.html).

If you want to clone this repositority (or a fork of it) to improve it, you can
proceed as follows:
1. Create a directory `ansible_collections/mcia`;
2. In there, checkout this repository (or a fork) as `irods`;
3. Add the directory containing `ansible_collections` to your [ANSIBLE_COLLECTIONS_PATH](https://docs.ansible.com/ansible/latest/reference_appendices/config.html#collections-paths).

See [Ansible's dev guide](https://docs.ansible.com/ansible/devel/dev_guide/developing_collections.html#contributing-to-collections) for more information.

## Licensing

[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)

## Authors

* Pierre Gay (@pigay)
