
# import dbt.utils.compiler_error
import networkx as nx

SELECTOR_PARENTS = '<'
SELECTOR_CHILDREN = '>'
SELECTOR_GLOB = '*'
SELECTOR_LOCAL_PACKAGE = 'this'


def parse_spec(node_spec):
    select_children = False
    select_parents = False
    index_start = 0
    index_end = len(node_spec)

    if node_spec.startswith(SELECTOR_PARENTS):
        select_parents = True
        index_start = 1

    if node_spec.endswith(SELECTOR_CHILDREN):
        select_children = True
        index_end -= 1

    node_selector = node_spec[index_start:index_end]
    # TODO: Validate node_selector here
    qualified_node_name = tuple(node_selector.split('.'))

    return {
        "select_parents": select_parents,
        "select_children": select_children,
        "qualified_node_name": qualified_node_name
    }


def get_package_names(graph):
    return set([node[0] for node in graph.nodes()])


def is_selected_node(real_node, node_selector):
    for i, selector_part in enumerate(node_selector):

        if selector_part == SELECTOR_GLOB:
            return True

        elif len(real_node) <= i:
            return False

        elif real_node[i] == selector_part:
            continue

        else:
            return False

    # if we get all the way down here, then the node is a match
    return True


def get_nodes_by_qualified_name(project, graph, qualified_name):
    """ returns a node if matched, else throws a CompilerError. qualified_name
    should be either 1) a node name or 2) a dot-notation qualified selector"""

    package_names = get_package_names(graph)

    for node in graph.nodes():
        if len(qualified_name) == 1 and node[-1] == qualified_name[0]:
            yield node

        elif qualified_name[0] in package_names:
            if is_selected_node(node, qualified_name):
                yield node

        elif qualified_name[0] == SELECTOR_LOCAL_PACKAGE:
            local_qualified_node_name = (project['name'],) + qualified_name[1:]
            if is_selected_node(node, local_qualified_node_name):
                yield node

        else:
            for package_name in package_names:
                local_qualified_node_name = (package_name,) + qualified_name
                if is_selected_node(node, local_qualified_node_name):
                    yield node
                    break


def get_nodes_from_spec(project, graph, spec):
    select_parents = spec['select_parents']
    select_children = spec['select_children']
    qualified_node_name = spec['qualified_node_name']

    selected_nodes = set(get_nodes_by_qualified_name(project,
                                                     graph,
                                                     qualified_node_name))

    additional_nodes = set()
    if select_parents:
        for node in selected_nodes:
            parent_nodes = nx.ancestors(graph, node)
            additional_nodes.update(parent_nodes)

    if select_children:
        for node in selected_nodes:
            child_nodes = nx.descendants(graph, node)
            additional_nodes.update(child_nodes)

    return selected_nodes | additional_nodes


def select_nodes(project, graph, raw_include_specs, raw_exclude_specs):
    selected_nodes = set()

    include_specs = [parse_spec(spec) for spec in raw_include_specs]
    exclude_specs = [parse_spec(spec) for spec in raw_exclude_specs]

    for spec in include_specs:
        included_nodes = get_nodes_from_spec(project, graph, spec)
        selected_nodes = selected_nodes | included_nodes

    for spec in exclude_specs:
        excluded_nodes = get_nodes_from_spec(project, graph, spec)
        selected_nodes = selected_nodes - excluded_nodes

    return selected_nodes