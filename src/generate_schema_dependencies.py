"""
Script to generate schema_dependencies.json from AWS CloudFormation DescribeType / ListTypes APIs.

This script:
1. Uses ListTypes to discover all resource types (FULLY_MUTABLE and IMMUTABLE, PUBLIC with AWS_TYPES category)
2. Uses DescribeType to get the full schema for each type
3. Parses handlers.list.handlerSchema to identify what properties the list handler needs
4. Cross-references with primaryIdentifier of other types to determine parent resources
5. Outputs a sorted/formatted JSON file with the dependency mappings

Usage:
    python generate_schema_dependencies.py

Requires valid AWS credentials.
"""

import json
import pathlib
import sys
import time
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

boto_config = BotoConfig(retries={"max_attempts": 10, "mode": "adaptive"})


def list_all_resource_types(cfn_client) -> list[str]:
    """List all resource types available via Cloud Control API."""
    resource_types = set()
    for pt in ["FULLY_MUTABLE", "IMMUTABLE"]:
        kwargs = {"ProvisioningType": pt, "DeprecatedStatus": "LIVE", "Type": "RESOURCE"}
        for page in cfn_client.get_paginator("list_types").paginate(
            Visibility="PUBLIC", Filters={"Category": "AWS_TYPES"}, **kwargs
        ):
            for summary in page["TypeSummaries"]:
                resource_types.add(summary["TypeName"])
    return sorted(resource_types)


def get_type_schema(cfn_client, type_name: str) -> Optional[dict]:
    """Get the parsed schema for a resource type using DescribeType."""
    try:
        response = cfn_client.describe_type(Type="RESOURCE", TypeName=type_name)
        schema = json.loads(response["Schema"])
        return schema
    except Exception as e:
        print(f"  Warning: Could not describe type {type_name}: {e}", file=sys.stderr)
        return None


def extract_list_handler_required(schema: dict) -> Optional[list[str]]:
    """Extract required properties from the list handler schema.

    Returns None if no list handler or no required properties are defined.
    """
    handlers = schema.get("handlers", {})
    list_handler = handlers.get("list", {})
    handler_schema = list_handler.get("handlerSchema", {})

    # Try 'required' field first
    required = handler_schema.get("required")
    if required:
        return required

    # Fall back to 'properties' keys if present (some schemas only define properties)
    properties = handler_schema.get("properties")
    if properties:
        return list(properties.keys())

    return None


def extract_primary_identifier_properties(schema: dict) -> list[str]:
    """Extract property names from primaryIdentifier paths.

    primaryIdentifier is like ["/properties/ClusterName", "/properties/AddonName"]
    Returns ["ClusterName", "AddonName"]
    """
    primary_ids = schema.get("primaryIdentifier", [])
    properties = []
    for path in primary_ids:
        # Format is /properties/PropertyName
        parts = path.split("/")
        if len(parts) >= 3 and parts[1] == "properties":
            properties.append(parts[2])
    return properties


def build_property_index(schemas: dict[str, dict]) -> dict[str, list[str]]:
    """Build an index mapping property names to resource types that have them as primary identifiers.

    Returns: {property_name: [type_name, ...]}
    """
    index: dict[str, list[str]] = {}
    for type_name, schema in schemas.items():
        primary_props = extract_primary_identifier_properties(schema)
        for prop in primary_props:
            index.setdefault(prop, []).append(type_name)
    return index


def find_parent_type(
    child_type: str,
    required_props: list[str],
    schemas: dict[str, dict],
) -> Optional[dict]:
    """Determine the parent resource type for a child based on required list properties.

    For a valid ResourceDependency, we need a single parent type whose primary identifier
    properties can supply all the required list handler properties of the child.

    Returns a dict with 'parent' and 'mapping' if found, None otherwise.
    """
    child_schema = schemas.get(child_type, {})
    child_primary_props = extract_primary_identifier_properties(child_schema)

    # The required properties for listing that are NOT part of the child's own primary identifier
    # are candidates. But actually, many times the required props ARE part of the primary identifier
    # of the child itself - e.g. ClusterName is part of the Addon's primary identifier.
    # We need to find a parent whose primary identifier includes properties that match.

    # Strategy: For each candidate parent type, check if its primary identifier properties
    # can provide all the required list properties (via property name matching or schema refs).

    # First, get all the property definitions from the child's schema
    child_properties = child_schema.get("properties", {})

    # For each required prop, try to find which parent type provides it
    # A required prop maps to a parent if the parent has a primary identifier property with
    # the same name, OR if the child's schema references indicate a relationship.

    # Simple heuristic: find a single parent type that has ALL required props as primary identifiers
    # This works for the majority of cases (e.g., EKS::Cluster has Name as primary ID,
    # and EKS::Addon requires ClusterName for listing).

    # Build candidate parents: for each required prop, find types whose primary identifier
    # includes a property that could match
    candidate_parents: dict[str, dict[str, str]] = {}  # {parent_type: {child_prop: parent_prop}}

    for req_prop in required_props:
        # Look through all schemas to find potential parents
        for parent_type, parent_schema in schemas.items():
            if parent_type == child_type:
                continue
            parent_primary_props = extract_primary_identifier_properties(parent_schema)
            for parent_prop in parent_primary_props:
                if _properties_match(req_prop, parent_prop, child_type, parent_type):
                    if parent_type not in candidate_parents:
                        candidate_parents[parent_type] = {}
                    candidate_parents[parent_type][req_prop] = parent_prop

    # Find a parent that covers ALL required props
    for parent_type, mapping in candidate_parents.items():
        if len(mapping) == len(required_props):
            # Prefer parents in the same service namespace
            return {"parent": parent_type, "mapping": mapping}

    # If no single parent covers all, try to find the best match from same service
    child_service = _get_service_prefix(child_type)
    same_service_candidates = {
        k: v for k, v in candidate_parents.items() if _get_service_prefix(k) == child_service
    }

    for parent_type, mapping in same_service_candidates.items():
        if len(mapping) == len(required_props):
            return {"parent": parent_type, "mapping": mapping}

    # Relax: if there is only one required prop, take the best same-service match
    if len(required_props) == 1:
        for parent_type, mapping in same_service_candidates.items():
            if len(mapping) >= 1:
                return {"parent": parent_type, "mapping": mapping}

    return None


def _get_service_prefix(type_name: str) -> str:
    """Get the service prefix from a type name like AWS::EKS::Cluster -> AWS::EKS"""
    parts = type_name.split("::")
    if len(parts) >= 2:
        return "::".join(parts[:2])
    return type_name


def _properties_match(child_prop: str, parent_prop: str, child_type: str, parent_type: str) -> bool:
    """Determine if a child's required property could be provided by a parent's primary identifier property.

    Uses heuristics based on naming conventions.
    """
    # Exact match
    if child_prop == parent_prop:
        return True

    # Common patterns where the child uses a different name:
    # Child: ClusterName, Parent: Name (same service)
    # Child: RestApiId, Parent: RestApiId
    # Child: AppId, Parent: AppId
    # Child: FlowArn, Parent: FlowArn

    child_service = _get_service_prefix(child_type)
    parent_service = _get_service_prefix(parent_type)

    # Only consider cross-property matching within the same service or related services
    if child_service != parent_service:
        return False

    # Pattern: child has "XyzName" or "XyzId" or "XyzArn", parent has "Name" or "Id" or "Arn"
    for suffix in ["Name", "Id", "Arn", "Identifier"]:
        if child_prop.endswith(suffix) and parent_prop == suffix:
            return True
        if parent_prop.endswith(suffix) and child_prop == suffix:
            return True

    # Pattern: child has "ParentTypeName" matching parent's "Name"
    parent_resource_name = parent_type.split("::")[-1] if "::" in parent_type else ""
    if child_prop == f"{parent_resource_name}{parent_prop}":
        return True
    if child_prop == f"{parent_resource_name}Name" and parent_prop == "Name":
        return True
    if child_prop == f"{parent_resource_name}Id" and parent_prop == "Id":
        return True
    if child_prop == f"{parent_resource_name}Arn" and parent_prop == "Arn":
        return True

    return False


def generate_dependencies(session: Optional[boto3.Session] = None) -> dict:
    """Main function to generate schema dependencies.

    Returns a dict mapping child_type -> {"parent": parent_type, "mapping": {child_prop: parent_prop}}
    """
    if session is None:
        session = boto3.Session()

    cfn = session.client("cloudformation", config=boto_config)

    print("Listing all resource types...", file=sys.stderr)
    resource_types = list_all_resource_types(cfn)
    print(f"Found {len(resource_types)} resource types", file=sys.stderr)

    # Fetch schemas for all types
    schemas: dict[str, dict] = {}
    total = len(resource_types)
    for i, type_name in enumerate(resource_types):
        if (i + 1) % 50 == 0:
            print(f"  Fetching schema {i + 1}/{total}...", file=sys.stderr)
        schema = get_type_schema(cfn, type_name)
        if schema:
            schemas[type_name] = schema

    print(f"Successfully fetched {len(schemas)} schemas", file=sys.stderr)

    # Find types that require properties for list operations
    dependencies: dict[str, dict] = {}
    for type_name, schema in schemas.items():
        required_props = extract_list_handler_required(schema)
        if not required_props:
            continue

        result = find_parent_type(type_name, required_props, schemas)
        if result:
            dependencies[type_name] = result

    print(f"Found {len(dependencies)} resource dependencies", file=sys.stderr)
    return dependencies


def main():
    dependencies = generate_dependencies()

    # Sort by key for stable output
    sorted_deps = dict(sorted(dependencies.items()))

    output_path = pathlib.Path(__file__).parent / "schema_dependencies.json"
    with open(output_path, "w") as f:
        json.dump(sorted_deps, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Written {len(sorted_deps)} dependencies to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
