import networkx as nx
import matplotlib.pyplot as plt


class DependencyGraph(object):
    def __init__(self):
        self._graph = nx.DiGraph()

    def add_resources(self, resources: list[str]):
        self._graph.add_nodes_from(resources)

    def add_dependency(self, resource, dependency):
        self._graph.add_edge(resource, dependency)

    def has_dependencies(self, resource):
        return bool(self._graph.predecessors(resource))

    def has_dependants(self, resource):
        return bool(self._graph.successors(resource))

    def recurse(self, from_resource: str):
        yield from_resource
        for resource in list(self._graph.successors(from_resource)):
            yield from self.recurse(resource)
