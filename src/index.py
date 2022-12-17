import datetime
import json
import pathlib
from os import path, environ
from typing import List, Set, Optional, Mapping

import boto3
import jmespath
from botocore.config import Config as BotoConfig

from config import EXCLUDES, EXCLUDES_GET, DEPENDENCIES
from dependency_utils import DependencyGraph, DynamicDependency, ResourceDependency, CheckEnabledDependency

boto_config = BotoConfig(retries={"max_attempts": 4, "mode": "adaptive"})
boto_session = boto3.Session()
cfn = boto_session.client("cloudformation", config=boto_config)
cc = boto_session.client("cloudcontrol", config=boto_config)


def main(resource_types: Optional[List] = None):
    if resource_types is None:
        resource_types = list_all_resource_types()
    graph = DependencyGraph(dependencies=DEPENDENCIES)
    graph.add_resources(resource_types)
    graph.load_dependencies()

    for chain_start in graph.root_nodes():
        known_resources = {}
        for resource_type in graph.walk(chain_start):
            resources = __get_resources(resource_type, known_resources)
            if resources is None:
                break  # end the whole chain, we skipped this resource type
            known_resources[resource_type] = resources
            print(f"{resource_type}: {len(known_resources[resource_type])}")
            write_resources_to_file(resource_type, known_resources[resource_type])


def list_all_resource_types() -> Set[str]:
    """List the parent_resource types that we can use with CloudControlApi."""
    # Supported types are FULLY_MUTABLE or IMMUTABLE and PUBLIC or PRIVATE
    for pt in ["FULLY_MUTABLE", "IMMUTABLE"]:
        kwargs = {"ProvisioningType": pt, "DeprecatedStatus": "LIVE", "Type": "RESOURCE"}
        # Public - return AWS types
        for page in cfn.get_paginator("list_types").paginate(
            Visibility="PUBLIC", Filters={"Category": "AWS_TYPES"}, **kwargs
        ):
            yield from (x["TypeName"] for x in page["TypeSummaries"])
        # Public - return activated types
        for page in cfn.get_paginator("list_types").paginate(
            Visibility="PUBLIC", Filters={"Category": "ACTIVATED"}, **kwargs
        ):
            yield from (x["TypeName"] for x in page["TypeSummaries"])
        # Private - return all types
        for page in cfn.get_paginator("list_types").paginate(Visibility="PRIVATE", **kwargs):
            yield from (x["TypeName"] for x in page["TypeSummaries"])


def list_resources_for_type(resource_type: str, resource_model: Optional[Mapping] = None) -> List:
    should_perform_get = resource_type not in EXCLUDES_GET  # always do at least one get
    kwargs = {}
    if resource_model:
        kwargs["ResourceModel"] = json.dumps(resource_model)

    try:
        for page in cc.get_paginator("list_resources").paginate(TypeName=resource_type, **kwargs):
            for description in page.get("ResourceDescriptions", []):  # AWS::IVS::StreamKey does not return this key
                if should_perform_get:
                    properties = cc.get_resource(TypeName=resource_type, Identifier=description["Identifier"])[
                        "ResourceDescription"
                    ]["Properties"]
                    if properties == description["Properties"]:
                        # we get no extra information, do not call getResource on the next iteration
                        # There is still a new request for a new resourceModel
                        should_perform_get = False
                else:
                    properties = description["Properties"]
                # parse nested json "string" to dictionary
                description["Properties"] = json.loads(properties)
                yield description
    except cc.exceptions.UnsupportedActionException:
        # List not supported
        pass


def write_resources_to_file(resource_type: str, resources: list, metadata: Optional[Mapping] = None):
    if metadata is None:
        metadata = {}
    folder = pathlib.Path("../output")
    folder.mkdir(exist_ok=True)
    file = folder / f"{resource_type.replace('::', '-').lower()}.json"
    if not resources and file.exists():
        file.unlink()
        return
    if not resources:
        return

    with open(file, "w") as fh:
        # We make this look like CloudFormation, so you can use tools like cfn-guard on it
        # This does not create valid templates":
        #   - the "LogicalResourceId" might contain invalid characters
        #   - read only properties are also written to the file
        #   - ...
        json.dump(
            {
                "Resources": {
                    x["Identifier"]: {
                        "Type": resource_type,
                        "Metadata": {"Identifier": x["Identifier"], **metadata},
                        "Properties": x["Properties"],
                    }
                    for x in resources
                }
            },
            fh,
            sort_keys=True,
            indent=2,
        )


def create_model(parent_resource: Mapping, property_mapping: Mapping):
    model = {}
    for resource_property, parent_property in property_mapping.items():
        previous = jmespath.search(parent_property, parent_resource["Properties"])
        assert previous is not None, "The jmespath search should return something"
        for key in reversed(resource_property.split(".")):
            previous = {key: previous}
        model.update(previous)

    return model


def __get_resources(resource_type, known_resources) -> Optional[List]:
    if resource_type in EXCLUDES:
        print(f"// {resource_type}: skipped")
        return None
    dependency = DEPENDENCIES.get(resource_type)

    if dependency is None:
        # We don't have to do anything special, we can list directly
        return list(list_resources_for_type(resource_type))

    if isinstance(dependency, CheckEnabledDependency):
        if dependency.function(session=boto_session):
            return list(list_resources_for_type(resource_type))
        return []  # this does not count as skipped, but as not enabled

    if isinstance(dependency, ResourceDependency):
        parent_type = DEPENDENCIES[resource_type].parent  # always one parent
        parent_resources = known_resources[parent_type]
    elif isinstance(dependency, DynamicDependency):
        parent_resources = dependency.function(session=boto_session)
    else:
        raise NotImplementedError("Unknown dependency type")

    output = []
    for resource in parent_resources:
        # construct a parent_resource model for every parent parent_resource that exists
        model = create_model(resource, DEPENDENCIES[resource_type].mapping)
        # Get all resources for the particular parent
        output.extend(list_resources_for_type(resource_type, model))
    return output


if __name__ == "__main__":
    start = datetime.datetime.utcnow()
    print(start.isoformat(" "))
    main()
    # main(
    #     [
    #         "AWS::WAFv2::IPSet",
    #         "AWS::WAFv2::RegexPatternSet",
    #         "AWS::WAFv2::RuleGroup",
    #         "AWS::WAFv2::WebACL",
    #         "AWS::QuickSight::Analysis",  # Required property: [AwsAccountId]
    #         "AWS::QuickSight::Dashboard",  # Required property: [AwsAccountId]
    #         "AWS::QuickSight::DataSet",  # Required property: [AwsAccountId]
    #         "AWS::QuickSight::DataSource",  # Required property: [AwsAccountId]
    #         "AWS::QuickSight::Template",  # Required property: [AwsAccountId]
    #         "AWS::QuickSight::Theme",  # Required property: [AwsAccountId]
    #         "AWS::AuditManager::Assessment",
    #         "AWS::CloudFormation::Publisher",
    #     ]
    # )
    stop = datetime.datetime.utcnow()
    print(stop.isoformat(" "))
    print(stop - start)
