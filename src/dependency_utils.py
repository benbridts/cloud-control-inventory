import dataclasses
from functools import lru_cache
from typing import Iterable, Optional, Mapping, Callable, List

import boto3
import networkx as nx


@dataclasses.dataclass
class ResourceDependency:
    parent: str
    mapping: dict[str, str]

    def get_parent_property(self, resource_property):
        return self.mapping[resource_property]


@dataclasses.dataclass
class DynamicDependency:
    function: Callable
    mapping: dict[str, str]


@dataclasses.dataclass
class CheckEnabledDependency:
    function: Callable


class DependencyGraph(object):
    def __init__(self, dependencies: Mapping[str, ResourceDependency]):
        self._graph = nx.DiGraph()
        self._dependencies = dependencies

    def add_resources(self, resources: Iterable[str]):
        self._graph.add_nodes_from(resources)

    def load_dependencies(self):
        for resource_type, dependency in self._dependencies.items():
            if not isinstance(dependency, ResourceDependency):
                continue  # not a real dependency
            if resource_type in self._graph.nodes and dependency.parent in self._graph.nodes:
                self._graph.add_edge(dependency.parent, resource_type)

    def has_dependencies(self, resource):
        # predecessors is an iterator, if there is at least a first element, return true
        for _ in self._graph.predecessors(resource):
            return True
        return False

    def has_dependants(self, resource):
        # successors is a iterator, if there is at least a first element, return true
        for _ in self._graph.successors(resource):
            return True
        return False

    def dependencies(self, resource):
        return self._graph.predecessors(resource)

    def dependants(self, resource):
        return self._graph.successors(resource)

    def walk(self, from_resource: str, parent: Optional[str] = None):
        yield from_resource
        for resource in list(self.dependants(from_resource)):
            yield from self.walk(resource, from_resource)

    def root_nodes(self):
        yield from (x for x in self._graph.nodes if not self.has_dependencies(x))


# This should always return the same values for the same session, we can cache it
@lru_cache(maxsize=None)
def list_wafv2_scopes(session: boto3.Session, **kwargs) -> List:
    scopes = [{"Properties": {"Scope": "REGIONAL"}}]  # always at least regional
    if session.region_name == "us-east-1":
        scopes.append({"Properties": {"Scope": "CLOUDFRONT"}})
    return scopes


# This should always return the same values for the same session, we can cache it
@lru_cache(maxsize=10)
def list_caller_identities(session: boto3.Session, **kwargs) -> List:
    session.client("sts").get_caller_identity()
    return [{"Properties": session.client("sts").get_caller_identity()}]


# This should always return the same values for the same session, we can cache it
@lru_cache(maxsize=10)
def list_quicksight_accounts(session: boto3.Session, **kwargs) -> List:
    account_id = session.client("sts").get_caller_identity()["Account"]
    qs = session.client("quicksight")
    try:
        qs.list_analyses(AwsAccountId=account_id)
        return [{"Properties": {"Account": account_id}}]
    except qs.exceptions.UnsupportedUserEditionException:
        # not subscribed to quicksight
        return []


# This should always return the same values for the same session, we can cache it
@lru_cache(maxsize=10)
def is_audit_manager_enabled(session: boto3.Session, **kwargs) -> bool:
    # Status can be ACTIVE | INACTIVE | PENDING_ACTIVATION
    return session.client("auditmanager").get_account_status()["status"] == "ACTIVE"


# This should always return the same values for the same session, we can cache it
@lru_cache(maxsize=10)
def is_cloudformation_publisher(session: boto3.Session, **kwargs) -> bool:
    cfn = session.client("cloudformation")
    try:
        # no arguments should try for this account
        cfn.describe_publisher()
        return True
    except cfn.exceptions.CFNRegistryException:
        return False
