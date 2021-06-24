from schema_classes import MariaDBDatabase
from services import network_handling
import azure.mgmt.resourcegraph as arg
import requests

def parse_obj(resource_type, resource_group, sub_id, name, rg_client, rg_query_options, resource_id, DEBUGGING, headers) -> MariaDBDatabase:
    str_query = f"resources | where type =~ 'microsoft.dbformariadb/servers' and name == '{name}'"
    query = arg.models.QueryRequest(
        subscriptions=[sub_id],
        query=str_query,
        options=rg_query_options,
    )
    try:
        rg_results_as_dict = rg_client.resources(query=query).__dict__
    except:
        if DEBUGGING:
            print(
                f"ERROR: Couldn't execute resource graph query of {name}, skipping asset."
            )
        return None
    raw_properties = rg_results_as_dict["data"][0]["properties"]
    try:
        privateEndpoints = raw_properties["privateEndpointConnections"]
    except KeyError:
        if DEBUGGING:
            print(
                f"Couldn't find privateEndpointConnections of MariaDB database {name}"
            )
        privateEndpoints = []
    try:
        publicNetworkAccess = raw_properties["publicNetworkAccess"]
    except KeyError:
        if DEBUGGING:
            print(
                f"Couldn't find publicNetworkAccess of MariaDB database {name}"
            )
        publicNetworkAccess = "Disabled"

    # To get firewall data from the resource explorer
    endpoint = f"https://management.azure.com/subscriptions/{sub_id}/resourceGroups/{resource_group}/providers/Microsoft.DBforMariaDB/servers/{name}/firewallRules?api-version=2017-12-01"
    try:
        resource_explorer_data = requests.get(
            url=endpoint, headers=headers
        ).json()
    except:
        resource_explorer_data = {}
        if DEBUGGING:
            print(
                f"Error running API call {endpoint}. Could be a bad authentication due to Bearer token."
            )
    firewallRules = []
    raw_firewallRules_data = resource_explorer_data.get("value")
    if raw_firewallRules_data:
        for raw_firewallRule in raw_firewallRules_data:
            try:
                start_ip_address = raw_firewallRule["properties"][
                    "startIpAddress"
                ]
                start_ip_components = raw_firewallRule["properties"][
                    "startIpAddress"
                ].split(".")
            except KeyError:
                start_ip_address = None
                start_ip_components = None
                if DEBUGGING:
                    print(
                        f"Could not get start ip from firewall rule {raw_firewallRule} in sql-server {name}."
                    )
            try:
                end_ip_address = raw_firewallRule["properties"][
                    "endIpAddress"
                ]
                end_ip_components = raw_firewallRule["properties"][
                    "endIpAddress"
                ].split(".")
            except KeyError:
                end_ip_address = None
                end_ip_components = None
                if DEBUGGING:
                    print(
                        f"Could not get end ip from firewall rule {raw_firewallRule} in sql-server {name}."
                    )
            temp_firewallRules = network_handling.handle_ip_range(
                start_ip_components,
                end_ip_components,
                start_ip_address,
                end_ip_address,
            )
            firewallRules = firewallRules + temp_firewallRules
    object_to_add = MariaDBDatabase(
        resourceId=resource_id,
        name=name,
        resourceGroup=resource_group,
        provider=resource_type,
        privateEndpoints=privateEndpoints,
        publicNetworkAccess=publicNetworkAccess,
        firewallRules=firewallRules,
    )
    return object_to_add