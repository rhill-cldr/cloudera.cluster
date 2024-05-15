# Copyright 2024 Cloudera, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from ansible.module_utils.common.text.converters import to_text, to_native

from ansible_collections.cloudera.cluster.plugins.module_utils.cm_utils import (
    ClouderaManagerModule,
    ClusterTemplate,
)

from ansible_collections.cloudera.cluster.plugins.module_utils.parcel_utils import (
    Parcel,
)

from cm_client import (
    ApiCluster,
    ApiClusterList,
    ApiClusterTemplate,
    ApiConfig,
    ApiConfigList,
    ApiDataContext,
    ApiHostRef,
    ApiHostRefList,
    ApiHostTemplate,
    ApiHostTemplateList,
    ApiRole,
    ApiRoleList,
    ApiRoleConfigGroup,
    ApiRoleConfigGroupRef,
    ApiRoleNameList,
    ApiService,
    ApiServiceConfig,
    ClouderaManagerResourceApi,
    ClustersResourceApi,
    HostsResourceApi,
    HostTemplatesResourceApi,
    ParcelResourceApi,
    ServicesResourceApi,
    RoleConfigGroupsResourceApi,
    RolesResourceApi,
)
from cm_client.rest import ApiException

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: cluster
short_description: Manage the lifecycle and state of a cluster
description:
  - Enables cluster management, cluster creation, deletion, and unified control of all services of a cluster.
  - Create or delete cluster in Cloudera Manager.
  - Start or stop all services inside the cluster.
  - If provided the C(template) parameter, the module will create a cluster based on the template.
author:
  - "Ronald Suplina (@rsuplina)"
  - "Webster Mudge (@wmudge)"
requirements:
  - cm_client
"""

EXAMPLES = r"""
---
- name: Create an ECS cluster
  cloudera.cluster.cluster:
    host: example.cloudera.com
    username: "jane_smith"
    password: "S&peR4Ec*re"
    port: 7180
    clusterName: example-cluster
    cluster_version: "1.5.1-b626.p0.42068229"
    cluster_type: EXPERIENCE_CLUSTER
    state: present

- name: Create a cluster from a cluster template
  cloudera.cluster.cm_cluster:
    host: example.cloudera.com
    username: "jane_smith"
    password: "S&peR4Ec*re"
    port: "7180"
    clusterName: example-cluster
    template: "./files/cluster-template.json"
    add_repositories: yes

- name: Start all services on a cluster
  cloudera.cluster.cluster:
    host: example.cloudera.com
    port: "7180"
    username: "jane_smith"
    password: "S&peR4Ec*re"
    clusterName: example-cluster
    state: started

- name: Delete a Cluster
  cloudera.cluster.cm_cluster:
    host: example.cloudera.com
    port: "7180"
    username: "jane_smith"
    password: "S&peR4Ec*re"
    clusterName: example-cluster
    state: absent
"""

RETURN = r"""
---
cloudera_manager:
    description: Details about Cloudera Manager Cluster
    type: dict
    contains:
        cluster_type:
            description: The type of cluster created from template.
            type: str
            returned: optional
        cluster_url:
            description: Url of Cloudera Manager cluster.
            type: str
            returned: optional
        display_name:
            description: The name of the cluster displayed on the site.
            type: str
            returned: optional
        entity_status:
            description: Health status of the cluster.
            type: str
            returned: optional
        full_version:
            description: Version of the cluster installed.
            type: str
            returned: optional
        hosts_url:
            description: Url of all the hosts on which cluster is installed.
            type: str
            returned: optional
        maintenance_mode:
            description: Maintance mode of Cloudera Manager Cluster.
            type: bool
            returned: optional
        maintenance_owners:
            description: List of Maintance owners for Cloudera Manager Cluster.
            type: list
            returned: optional
        name:
            description: The name of the cluster created.
            type: str
            returned: optional
        tags:
            description: List of tags for Cloudera Manager Cluster.
            type: list
            returned: optional
        uuid:
            description: Unique ID of created cluster
            type: bool
            returned: optional
"""


class ClouderaCluster(ClouderaManagerModule):
    def __init__(self, module):
        super(ClouderaCluster, self).__init__(module)

        self.name = self.get_param("name")
        self.cluster_version = self.get_param("cluster_version")
        self.type = self.get_param("type")
        self.state = self.get_param("state")
        self.template = self.get_param("template")
        self.add_repositories = self.get_param("add_repositories")
        self.maintenance = self.get_param("maintenance")
        self.hosts = self.get_param("hosts")
        self.host_templates = self.get_param("host_templates")
        self.services = self.get_param("services")
        self.parcels = self.get_param("parcels")
        self.tags = self.get_param("tags")
        self.display_name = self.get_param("display_name")
        self.contexts = self.get_param("contexts")
        self.auto_assign = self.get_param("auto_assign")

        self.changed = False
        self.output = {}

        self.delay = 15  # TODO Parameterize
        self.timeout = 7200  # TODO Parameterize
        self.message = "Ansible-powered"  # TODO Parameterize

        self.process()

    @ClouderaManagerModule.handle_process
    def process(self):
        self.cm_api = ClouderaManagerResourceApi(self.api_client)
        self.cluster_api = ClustersResourceApi(self.api_client)
        self.service_api = ServicesResourceApi(self.api_client)
        self.host_template_api = HostTemplatesResourceApi(self.api_client)
        self.host_api = HostsResourceApi(self.api_client)
        self.role_group_api = RoleConfigGroupsResourceApi(self.api_client)
        self.role_api = RolesResourceApi(self.api_client)

        refresh = True

        # TODO manage services following the ClusterTemplateService data model
        # TODO manage host and host template assignments following the ClusterTemplateHostInfo data model
        # TODO manage host templates following the ClusterTemplateHostTemplate data model
        # TODO manage role config groups following the ClusterTemplateRoleConfigGroupInfo data model (-CREATE-, MODIFY)
        # TODO cluster template change management
        # TODO auto assign roles (xCREATEx, MODIFY)
        # TODO auto configure services and roles
        # TODO auto-TLS (separate module for full credential lifecycle)
        # TODO configure KRB (separate module for full KRB lifecycle)
        # TODO deploy client configs (services)
        # TODO auto-upgrade (bool: False) including prechecks
        # TODO refresh configurations (bool: True, set False to suppress restarts)
        # TODO restart arguments (selective restarts)
        # TODO rolling restart arguments
        # TODO rolling upgrade arguments
        # TODO cluster object return

        # Retrieve existing cluster
        existing = None
        try:
            existing = self.cluster_api.read_cluster(cluster_name=self.name)
        except ApiException as ex:
            if ex.status != 404:
                raise ex

        # Prepare any cluster template content
        template_contents = None
        if self.template:
            try:
                with open(self.template, "r", encoding="utf-8") as file:
                    template_contents = json.load(file)
            except OSError as oe:
                self.module.fail_json(
                    msg=f"Error reading cluster template file, '{to_text(self.template)}'",
                    err=to_native(oe),
                )

        if self.state == "present":
            # Modify cluster
            if existing:
                self.module.warn(
                    "Module currently does not support reconcilation of cluster templates with existing clusters."
                )
                refresh = False

                # Reconcile the existing vs. the incoming values into a set of diffs
                # then process via the PUT /clusters/{clusterName} endpoint

                if self.auto_assign:
                    self.changed = True
                    if not self.module.check_mode:
                        self.cluster_api.auto_assign_roles(cluster_name=self.name)
                        refresh = True
            # Create cluster
            else:
                # TODO import_cluster_template appears to construct and first run the cluster, which is NOT what present should do
                # That would mean import_cluster_template should only be executed on a fresh cluster with 'started' or 'restarted' states
                if template_contents:
                    self.create_cluster_from_template(template_contents)
                else:
                    self.create_cluster_from_parameters()

        elif self.state == "absent":
            # Delete cluster

            refresh = False

            # TODO Check for status when deleting
            # if existing and existing.entity_status == "":
            #     self.wait_for_active_cmd(cluster_api, self.cluster_name)
            # elif existing:
            if existing:
                self.changed = True
                if not self.module.check_mode:
                    self.cluster_api.delete_cluster(cluster_name=self.name)
                    self.wait_for_active_cmd(self.name)

        elif self.state == "started":
            # TODO NONE seems to be fresh cluster, never run before
            # Already started
            if existing and existing.entity_status == "GOOD_HEALTH":
                refresh = False
                pass
            # Start underway
            elif existing and existing.entity_status == "STARTING":
                self.wait_for_active_cmd(self.name)
            # Needs starting
            else:
                # Create if needed
                if not existing:
                    if template_contents:
                        self.create_cluster_from_template(template_contents)
                    else:
                        self.create_cluster_from_parameters()

                self.changed = True
                if not self.module.check_mode:
                    # If newly created or created by not yet initialize
                    if not existing or existing.entity_status == "NONE":
                        first_run = self.cluster_api.first_run(cluster_name=self.name)
                        self.wait_for_composite_cmd(first_run.id)
                    # Start the existing and previously initialized cluster
                    else:
                        start = self.cluster_api.start_command(cluster_name=self.name)
                        self.wait_for_composite_cmd(start.id)

        if self.state == "stopped":
            # Already stopped
            if existing and existing.entity_status == "STOPPED":
                refresh = False
                pass
            # Stop underway
            elif existing and existing.entity_status == "STOPPING":
                self.wait_for_active_cmd(self.name)
            # Needs stopping
            else:
                # Create if needed
                if not existing:
                    if template_contents:
                        self.create_cluster_from_template(template_contents)
                    else:
                        self.create_cluster_from_parameters()
                # Stop an existing cluster
                else:
                    self.changed = True
                    if not self.module.check_mode:
                        stop = self.cluster_api.stop_command(cluster_name=self.name)
                        self.wait_for_composite_cmd(stop.id)

        if self.state == "restarted":
            # Start underway
            if existing and existing.entity_status == "STARTING":
                self.wait_for_active_cmd(self.name)
            # Needs restarting
            else:
                # Create if needed
                if not existing:
                    if template_contents:
                        self.create_cluster_from_template(template_contents)
                    else:
                        self.create_cluster_from_parameters()

                self.changed = True
                if not self.module.check_mode:
                    restart = self.cluster_api.restart_command(cluster_name=self.name)
                    self.wait_for_composite_cmd(restart.id)

        if refresh:
            # Retrieve the updated cluster details
            self.output = self.cluster_api.read_cluster(
                cluster_name=self.name
            ).to_dict()
        elif existing:
            self.output = existing.to_dict()

    def wait_for_composite_cmd(self, command_id: str):
        cmd = self.wait_for_command_state(
            command_id=command_id,
            polling_interval=self.delay,
        )
        if not cmd[0].success:
            collected_msgs = [
                f"[{c.name}] {c.result_message}"
                for c in cmd[0].children.items
                if not c.success
            ]
            self.module.fail_json(msg="\n".join(collected_msgs))
        elif not cmd:
            self.module.fail_json(msg="Invalid command result", cmd=to_native(cmd))

        return cmd

    def wait_for_active_cmd(self, cluster_name: str):
        active_cmd = None
        try:
            active_cmd = next(
                iter(
                    self.cluster_api.list_active_commands(
                        cluster_name=cluster_name
                    ).items
                ),
                None,
            )
        except ApiException as e:
            if e.status != 404:
                raise e

        if active_cmd:
            self.wait_for_command_state(
                command_id=active_cmd.id,
                polling_interval=self.delay,
            )

    def create_cluster_from_template(self, template_contents: dict):
        payload = dict()

        # Construct import template payload from the template and/or explicit parameters
        explicit_params = dict()

        # Set up 'instantiator' parameters
        explicit_params.update(instantiator=dict(clusterName=self.name))

        # Merge/overlay any explicit parameters over the template
        TEMPLATE = ClusterTemplate(
            warn_fn=self.module.warn, error_fn=self.module.fail_json
        )
        TEMPLATE.merge(template_contents, explicit_params)
        payload.update(body=ApiClusterTemplate(**template_contents))

        # Update to include repositories
        if self.add_repositories:
            payload.update(add_repositories=True)

        # Execute the import
        self.changed = True
        if not self.module.check_mode:
            import_template_request = self.cm_api.import_cluster_template(
                **payload
            ).to_dict()

            command_id = import_template_request["id"]
            self.wait_for_command_state(
                command_id=command_id, polling_interval=self.delay
            )

    def create_cluster_from_parameters(self):
        if self.cluster_version is None:
            self.module.fail_json(
                msg=f"Cluster must be created. Missing required parameter: cluster_version"
            )

        # Configure the core cluster
        cluster = ApiCluster(
            name=self.name,
            full_version=self.cluster_version,
            cluster_type=self.type,
        )

        # Configure cluster services
        if self.services:
            cluster.services = [self.marshal_service(s) for s in self.services]

        # Configure cluster contexts
        if self.contexts:
            cluster.data_context_refs = [ApiDataContext(name=d) for d in self.contexts]

        # Execute the creation
        self.changed = True

        if not self.module.check_mode:
            # Validate any incoming host membership to fail fast
            if self.hosts:
                hostrefs = self.marshal_hostrefs({h["name"]: h for h in self.hosts})
                hostref_by_host_id = {h.host_id: h for h in hostrefs}
                hostref_by_hostname = {h.hostname: h for h in hostrefs}

            # Create the cluster configuration
            self.cluster_api.create_clusters(body=ApiClusterList(items=[cluster]))
            self.wait_for_active_cmd(self.name)

            # Add host templates to cluster
            if self.host_templates:

                # Prepare host template role group assignments
                # and discover base role groups if needed
                templates = [
                    ApiHostTemplate(
                        name=ht["name"],
                        role_config_group_refs=[
                            ApiRoleConfigGroupRef(
                                rcg["name"]
                                if rcg["name"]
                                else self.find_base_role_group_name(
                                    service_type=rcg["service"], role_type=rcg["type"]
                                )
                            )
                            for rcg in ht["role_groups"]
                        ],
                    )
                    for ht in self.host_templates
                ]

                self.host_template_api.create_host_templates(
                    cluster_name=self.name,
                    body=ApiHostTemplateList(items=templates),
                )

            # Add hosts to cluster and set up assignments
            template_map = {}
            role_group_list = []
            role_list = []

            if self.hosts:
                # Add the hosts
                self.cluster_api.add_hosts(
                    cluster_name=self.name,
                    body=ApiHostRefList(items=hostrefs),
                )

                for h in self.hosts:
                    # Normalize hostref
                    hostref = (
                        hostref_by_host_id[h["name"]]
                        if h["name"] in hostref_by_host_id
                        else hostref_by_hostname[h["name"]]
                    )

                    # Prepare host template assignments
                    if h["host_template"]:
                        if h["host_template"] in template_map:
                            template_map[h["host_template"]].append(hostref)
                        else:
                            template_map[h["host_template"]] = [hostref]

                    # Prepare role group assignments
                    if h["role_groups"]:
                        role_group_list.append((hostref, h["role_groups"]))

                    # Prepare role overrides
                    if h["roles"]:
                        role_list.append((hostref, h["roles"]))

            # Activate parcels
            if self.parcels:
                parcel_api = ParcelResourceApi(self.api_client)
                for p, v in self.parcels.items():
                    parcel = Parcel(
                        parcel_api=parcel_api,
                        product=p,
                        version=v,
                        cluster=self.name,
                        delay=self.delay,
                        timeout=self.timeout,
                    )
                    parcel.activate()

            # Apply host templates
            for ht, refs in template_map.items():
                self.host_template_api.apply_host_template(
                    cluster_name=self.name,
                    host_template_name=ht,
                    start_roles=False,
                    body=ApiHostRefList(items=refs),
                )

            # Configure direct role group assignments
            if role_group_list:
                # Gather all the RCGs for all services, as the host template might
                # not reference RCGs that are directly configured in the service
                # definition, i.e. base role groups
                all_rcgs = {
                    rcg.name: (
                        rcg.base,
                        s.name,
                        rcg.role_type,
                    )
                    for s in self.service_api.read_services(
                        cluster_name=self.name
                    ).items  # s.name
                    for rcg in self.role_group_api.read_role_config_groups(
                        cluster_name=self.name, service_name=s.name
                    ).items
                }

                for hostref, host_rcgs in role_group_list:
                    for rcg in host_rcgs:
                        rcg_ref = None

                        if rcg["name"]:
                            # Use the declared RCG name
                            if rcg["name"] not in all_rcgs:
                                self.module.fail_json(
                                    msg="Role config group '%s' not found on cluster."
                                    % rcg["name"]
                                )
                            else:
                                rcg_ref = all_rcgs[rcg["name"]]
                        else:
                            # Or discover the role group
                            rcg_name = next(
                                iter(
                                    [
                                        name
                                        for name, refs in all_rcgs.items()
                                        if refs[0]
                                        and refs[1] == rcg["service"]
                                        and refs[2] == rcg["type"]
                                    ]
                                ),
                                None,
                            )

                            if rcg_name is None:
                                self.module.fail_json(
                                    msg="Unable to find base role group, '%s [%s]', on cluster, '%s'"
                                    % (rcg["service"], rcg["type"], self.name)
                                )

                            rcg_ref = all_rcgs[rcg_name]

                        # Add the role of that type to the host (generating a name)
                        direct_roles = self.role_api.create_roles(
                            cluster_name=self.name,
                            service_name=rcg_ref[1],
                            body=ApiRoleList(
                                items=[ApiRole(type=rcg_ref[2], host_ref=hostref)]
                            ),
                        )

                        # Move the newly-created role to the RCG if it is not a base/default group
                        if not rcg_ref[0]:
                            self.role_group_api.move_roles(
                                cluster_name=self.name,
                                role_config_group_name=rcg["name"],
                                service_name=rcg_ref[1],
                                body=ApiRoleNameList(
                                    items=[direct_roles.items[0].name]
                                ),
                            )

            # Configure per-host role overrides
            for (
                hostref,
                overrides,
            ) in role_list:
                for override in overrides:
                    # Discover the role on the host
                    host_role = next(
                        iter(
                            self.role_api.read_roles(
                                cluster_name=self.name,
                                service_name=override["service"],
                                filter="type==%s;hostId==%s"
                                % (override["type"], hostref.host_id),
                            ).items
                        ),
                        None,
                    )

                    if host_role is not None:
                        self.role_api.update_role_config(
                            cluster_name=self.name,
                            service_name=override["service"],
                            role_name=host_role.name,
                            message=self.message,
                            body=ApiConfigList(
                                items=[
                                    ApiConfig(name=k, value=v)
                                    for k, v in override["config"].items()
                                ]
                            ),
                        )
                    else:
                        self.module.fail_json(
                            msg="Role not found. No role type '%s' for service '%s' found on host '%s'"
                            % (override["type"], override["service"], hostref.hostname)
                        )

            # Execute auto-role assignments
            if self.auto_assign:
                self.cluster_api.auto_assign_roles(cluster_name=self.name)

    def marshal_service(self, options: str) -> ApiService:
        service = ApiService(name=options["name"], type=options["type"])

        if "display_name" in options:
            service.display_name = options["display_name"]

        # Service-wide configuration
        if options["config"]:
            service.config = ApiServiceConfig(
                items=[ApiConfig(name=k, value=v) for k, v in options["config"].items()]
            )

        if options["role_groups"]:
            rcg_list = []

            for body in options["role_groups"]:
                rcg = ApiRoleConfigGroup(role_type=body["type"])

                # Either a defined role group or a default/base group
                if body["name"]:
                    rcg.name = body["name"]
                else:
                    rcg.base = True

                if body["display_name"]:
                    rcg.display_name = body["display_name"]

                if body["config"]:
                    rcg.config = ApiConfigList(
                        items=[
                            ApiConfig(name=k, value=v)
                            for k, v in body["config"].items()
                        ]
                    )

                rcg_list.append(rcg)

            service.role_config_groups = rcg_list

        if "tags" in options:
            pass

        if "version" in options:
            pass

        return service

    def marshal_hostrefs(self, hosts: dict) -> list[ApiHostRef]:
        results = []
        hosts_query = self.host_api.read_hosts().items
        for h in hosts_query:
            if h.host_id in hosts.keys() or h.hostname in hosts.keys():
                if (
                    h.cluster_ref is not None
                    and h.cluster_ref.cluster_name != self.name
                ):
                    self.module.fail_json(
                        msg=f"Invalid host reference! Host {h.hostname} ({h.host_id}) already in use with cluster '{h.cluster_ref.cluster_name}'!"
                    )
                results.append(ApiHostRef(host_id=h.host_id, hostname=h.hostname))
        if len(results) != len(hosts.keys()):
            self.module.fail_json(
                msg="Did not find the following hosts: "
                + ", ".join(set(hosts.keys() - set(results)))
            )
        return results

    def find_base_role_group_name(
        self, service_type: str, role_type: str
    ) -> ApiRoleConfigGroup:
        rcgs = [
            rcg
            for s in self.service_api.read_services(cluster_name=self.name).items
            for rcg in self.role_group_api.read_role_config_groups(
                cluster_name=self.name, service_name=s.name
            ).items
            if s.type == service_type
        ]

        base = next(
            iter([rcg for rcg in rcgs if rcg.base and rcg.role_type == role_type]),
            None,
        )

        if base is None:
            self.module.fail_json(
                "Invalid role group; unable to discover base role group for service role, %s[%s]"
                % (role_type, service_type)
            )
        else:
            return base.name


def main():
    module = ClouderaManagerModule.ansible_module(
        argument_spec=dict(
            name=dict(required=True, aliases=["cluster_name"]),
            cluster_version=dict(),
            type=dict(
                aliases=["cluster_type"],
                choices=["BASE_CLUSTER", "COMPUTE_CLUSTER", "EXPERIENCE_CLUSTER"],
            ),
            state=dict(
                default="present",
                choices=["present", "absent", "stopped", "started", "restarted"],
            ),
            # A cluster template used as the "baseline" for the parameters
            template=dict(type="path", aliases=["cluster_template"]),
            # Only valid if using 'template'
            add_repositories=dict(type="bool", default=False),
            # Flag for warning suppression
            maintenance=dict(type="bool", aliases=["maintenance_enabled"]),
            # Services, service configs, role config groups
            services=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(aliases=["ref", "ref_name"]),
                    type=dict(required=True),
                    version=dict(),
                    # Service-level config
                    config=dict(type="dict"),
                    # Role config groups (RCG)
                    role_groups=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(aliases=["ref", "ref_name"]),
                            type=dict(required=True, aliases=["role_type"]),
                            display_name=dict(),
                            config=dict(type="dict"),
                        ),
                        aliases=["role_config_groups"],
                    ),
                    display_name=dict(),
                    tags=dict(type="dict"),
                ),
            ),
            # Hosts, host template assignments, explicit role group assignments, and per-host role overrides
            hosts=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(required=True, aliases=["host_id", "hostname"]),
                    config=dict(),
                    host_template=dict(),
                    role_groups=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            name=dict(aliases=["ref", "ref_name"]),
                            service=dict(required=True, aliases=["service_name"]),
                            type=dict(aliases=["role_type"]),
                        ),
                        aliases=["role_config_groups"],
                        mutually_exclusive=[
                            ("name", "type"),
                        ],
                    ),
                    roles=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            service=dict(
                                required=True, aliases=["service_name", "service_ref"]
                            ),
                            type=dict(required=True, aliases=["role_type"]),
                            config=dict(type="dict", required=True),
                        ),
                    ),
                    tags=dict(),
                ),
            ),
            # Host templates
            host_templates=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(required=True),
                    role_groups=dict(
                        type="list",
                        elements="dict",
                        required=True,
                        options=dict(
                            name=dict(aliases=["ref", "ref_name"]),
                            service=dict(required=True, aliases=["service_name"]),
                            type=dict(aliases=["role_type"]),
                        ),
                        aliases=["role_config_groups"],
                        mutually_exclusive=[
                            ("name", "type"),
                        ],
                    ),
                ),
            ),
            # Parcels is a dict of product:version of the cluster
            parcels=dict(type="dict", aliases=["products"]),
            # Tags is a dict of key:value assigned to the cluster
            tags=dict(),
            # Optional UI name
            display_name=dict(),
            # Optional data contexts, required for compute-type clusters
            contexts=dict(type="list", elements="str", aliases=["data_contexts"]),
            # Optional enable/disable TLS for the cluster
            tls=dict(type="bool", aliases=["tls_enabled", "cluster_tls"]),
            # Optional auto-assign roles on cluster (honors existing assignments)
            auto_assign=dict(type="bool", default=False, aliases=["auto_assign_roles"]),
        ),
        supports_check_mode=True,
        mutually_exclusive=[
            ("cdh_version", "cdh_short_version"),
        ],
        required_if=[("type", "COMPUTE_CLUSTER", ("contexts"))],
    )

    result = ClouderaCluster(module)

    changed = result.changed

    output = dict(
        changed=changed,
        cloudera_manager=result.output,
    )

    if result.debug:
        log = result.log_capture.getvalue()
        output.update(debug=log, debug_lines=log.split("\n"))

    module.exit_json(**output)


if __name__ == "__main__":
    main()
