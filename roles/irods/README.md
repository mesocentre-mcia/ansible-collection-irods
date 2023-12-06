iRODS
=========

Installs and configures iRODS service on RHEL/CentOS or Ubuntu (18.04 bionic) servers.  
Catalog database is installed with PostgreSQL backend.

Requirements
------------

This role requires:
* `geerlingguy.postgresql` role
* optionally `community.crypto` collection if selfsigned certificates are to be
  produced

Role Variables
--------------

Available variables are listed below, along with default values (see `defaults/main.yml`):

    irods_zone_name: "demoZone"

Name of the server's zone.

    irods_catalog_provider_hosts: ["localhost"]

List of catalog provider servers.

    irods_hosts: []

List of other hosts in the configured zone (resource servers).

**Note: Each iRODS host should define a variable `irods_ip` in the inventory, corresponding to the IP address of the iRODS server.** If not the case, this role will use ansible gathered facts.

    irods_default_resource_name: "demoResc"

Name of default resource (used in `server_config.json` and service account `irods_environment.json`).

    irods_version: null

iRODS version to install (`null` is latest version)

    irods_cs_ssl: false

Client/server SSL negotiation.

    irods_db_host: "localhost"
    irods_db_name: "ICAT"
    irods_db_odbc_driver: "PostgreSQL"
    irods_db_port: 5432
    irods_db_username: "irods"

PostgreSQL configuration options.

    irods_zone_port: 1247
    irods_server_control_plane_port: 1248
    irods_xmsg_port: 1279

    irods_server_port_range_start: 20000
    irods_server_port_range_end: 20199

iRODS network ports.

    irods_zone_user: "rods"

iRODS zone admin user name.

    irods_ssl_default_directory: "/etc/irods/certs"
    irods_ssl_certificate_chain_file: "{{ irods_ssl_default_directory }}/server.crt"
    irods_ssl_certificate_key_file: "{{ irods_ssl_default_directory }}/server.key"
    irods_ssl_verify_server: "hostname"
    irods_ssl_ca_certificate_file: "{{ irods_ssl_default_directory }}/ca.crt"

SSL configuration options. Certificates are to be provided separately or created
with selfsigned provided task (see Playbook examples below).

Some mandatory variables don't have a default value. They are your zone's secret
values (passwords, secret keys, etc.). **You must define these**, preferably
with random/hard to guess values:

* `irods_admin_password`
* `irods_database_user_password_salt`
* `irods_zone_key`
* `irods_db_password`
* `irods_negotiation_key`: has to be a 32 bytes long string
* `irods_server_control_plane_key`: has to be a 32 bytes long string

Example Playbook
----------------

Here is a two hosts example playbook:
* host `icat` is the catalog provider
* host `irods0` is at the same time the database server and a resource server
* client/server SSL negotiation is requested
* server self-signed certificates are installed

```yaml
    - name: Converge
      hosts: all
      vars:
        irods_catalog_provider_hosts: ['icat']
        irods_hosts: ['icat', 'irods0']
        irods_db_host: 'irods0'
        irods_admin_password: "VERY_SECRET_ADMIN_PASSWORD"
        irods_database_user_password_salt: "VERY_SECRET_SALT"
        irods_negotiation_key: "09876543210987654321098765432109"
        irods_db_password: "VERY_SECRET_PASSWORD"
        irods_server_control_plane_key: "12345678901234567890123456789012"
        irods_zone_key: "VERY_SECRET_KEY"
        irods_cs_ssl: true
      tasks:
        # database stuff
        - include_role:
            # catalog needs to know how to connect to irods_db_host
            name: irods
            tasks_from: "fill-etc-hosts"

        - name: "Configure host as a database server"
          include_role:
            name: irods
            tasks_from: "database-role-PostgreSQL"
          when: inventory_hostname == irods_db_host

        - name: "create iRODS database on server"
          include_role:
            name: irods
            tasks_from: "database-configure-PostgreSQL"
          when: inventory_hostname == irods_db_host

        # prepare hosts for SSL setup with self-signed certificates
        - name: "Include ansible-role-irods"
          include_role:
            name: irods
            tasks_from: "create_selfsigned_certificates.yml"

        # run irods role
        - name: "Include irods ansible role"
          include_role:
            name: irods
```
