"""
A taxonomy is a hierarchical structure of categories, where each category is a node in the taxonomy.
The nodes are connected by parent-child relationships, and the root node is the top-level category.
Each node may have the attributes `name`, `weight`, and `children` (see `cbrkit.sim.strings.taxonomy.SerializedTaxonomyNode`).
To simplify the creation of a taxonomy, the `cbrkit.sim.strings.taxonomy.load` function can be used to load a taxonomy from a file (toml, json, or yaml).
For nodes without a `weight` or `children`, it is also possible to pass its name as a string instead of a dictionary.

**Important:** If loading the taxonomy from a file, changes like adding children or weights need to be made there, not in the code.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Protocol, TypedDict, cast, override

from ...helpers import get_metadata
from ...loaders import data as load_data
from ...typing import FilePath, JsonDict, SimPairFunc, SupportsMetadata

__all__ = [
    "load",
    "wu_palmer",
    "user_weights",
    "auto_weights",
    "node_levels",
    "path_steps",
    "Taxonomy",
    "TaxonomyNode",
    "SerializedTaxonomyNode",
    "TaxonomyFunc",
    "TaxonomyStrategy",
]


class SerializedTaxonomyNode(TypedDict, total=False):
    name: str
    weight: float
    children: list["SerializedTaxonomyNode | str"]


@dataclass(slots=True)
class TaxonomyNode:
    name: str
    weight: float
    depth: int
    parent: Optional["TaxonomyNode"]
    children: dict[str, "TaxonomyNode"] = field(default_factory=dict)

    @property
    def level(self) -> int:
        return self.depth + 1


class Taxonomy:
    __slots__ = ("root", "nodes")

    root: TaxonomyNode
    nodes: dict[str, TaxonomyNode]

    def __init__(self, path: FilePath) -> None:
        root_data = cast(SerializedTaxonomyNode, load_data(path))
        self.nodes = {}
        self.root = self._load(root_data)

    @property
    def max_depth(self) -> int:
        return max(node.depth for node in self.nodes.values())

    @property
    def max_level(self) -> int:
        return max(node.level for node in self.nodes.values())

    def _load(
        self,
        data: SerializedTaxonomyNode | str,
        parent: TaxonomyNode | None = None,
        depth: int = 0,
    ) -> TaxonomyNode:
        if isinstance(data, str):
            data = {"name": data}

        assert "name" in data, "Missing name in some node"

        node = TaxonomyNode(
            name=data["name"],
            weight=data.get("weight", 1.0),
            depth=depth,
            parent=parent,
        )

        for child in data.get("children", []):
            child_node = self._load(child, node, depth + 1)
            node.children[child_node.name] = child_node

        self.nodes[node.name] = node

        return node

    def lca(self, node1: TaxonomyNode, node2: TaxonomyNode) -> TaxonomyNode:
        while node1 != node2:
            if node1.parent is None or node2.parent is None:
                return self.root

            if node1.depth > node2.depth:
                node1 = node1.parent
            else:
                node2 = node2.parent

        return node1


class TaxonomyFunc(Protocol):
    def __call__(self, taxonomy: Taxonomy, x: str, y: str) -> float: ...


TaxonomyStrategy = Literal["optimistic", "pessimistic", "average"]


@dataclass(slots=True, frozen=True)
class wu_palmer(TaxonomyFunc, SupportsMetadata):
    """Wu & Palmer similarity measure of two nodes in a taxonomy.

    Examples:
        >>> taxonomy = Taxonomy("./data/cars-taxonomy.yaml")
        >>> sim = wu_palmer()
        >>> sim(taxonomy, "audi", "porsche")
        0.5
        >>> sim(taxonomy, "audi", "bmw")
        0.0
    """

    @override
    def __call__(self, taxonomy: Taxonomy, x: str, y: str) -> float:
        node1 = taxonomy.nodes[x]
        node2 = taxonomy.nodes[y]
        lca = taxonomy.lca(node1, node2)

        return (2 * lca.depth) / (node1.depth + node2.depth)


@dataclass(slots=True, frozen=True)
class user_weights(TaxonomyFunc, SupportsMetadata):
    """User-defined weights similarity measure of two nodes in a taxonomy.

    The weights are defined by the user in the taxonomy file.

    Args:
        strategy: The strategy to use in case one of the node is the lowest common ancestor (lca).
            One of "optimistic", "pessimistic", or "average".

    ![user weights](../../../../assets/taxonomy/user-weights.png)

    Examples:
        >>> taxonomy = Taxonomy("./data/cars-taxonomy.yaml")
        >>> sim = user_weights("optimistic")
        >>> sim(taxonomy, "audi", "Volkswagen AG")
        1.0
        >>> sim(taxonomy, "audi", "bmw")
        0.0
    """

    strategy: TaxonomyStrategy

    @override
    def __call__(self, taxonomy: Taxonomy, x: str, y: str) -> float:
        node1 = taxonomy.nodes[x]
        node2 = taxonomy.nodes[y]
        lca = taxonomy.lca(node1, node2)
        weight = lca.weight

        if lca == node1 or lca == node2:
            # pessimistic not needed: weight of lca already used
            if self.strategy == "optimistic":
                weight = 1.0
            elif self.strategy == "average":
                weight = (node1.weight + node2.weight) / 2

        return weight


@dataclass(slots=True, frozen=True)
class auto_weights(TaxonomyFunc, SupportsMetadata):
    """Automatic weights similarity measure of two nodes in a taxonomy.

    The weights are automatically calculated based on the depth of the nodes.

    Args:
        strategy: The strategy to use in case one of the node is the lowest common ancestor (lca).
            One of "optimistic", "pessimistic", or "average".

    ![auto weights](../../../../assets/taxonomy/auto-weights.png)

    Examples:
        >>> taxonomy = Taxonomy("./data/cars-taxonomy.yaml")
        >>> sim = auto_weights("optimistic")
        >>> sim(taxonomy, "audi", "Volkswagen AG")
        1.0
        >>> sim(taxonomy, "audi", "bmw")
        0.0
    """

    strategy: TaxonomyStrategy

    @override
    def __call__(self, taxonomy: Taxonomy, x: str, y: str) -> float:
        node1 = taxonomy.nodes[x]
        node2 = taxonomy.nodes[y]
        lca = taxonomy.lca(node1, node2)
        max_depth = taxonomy.max_depth

        weight = lca.depth / max_depth

        if lca == node1 or lca == node2:
            # pessimistic not needed: weight of lca already used
            if self.strategy == "optimistic":
                weight = 1.0
            elif self.strategy == "average":
                weight1 = node1.depth / max_depth
                weight2 = node2.depth / max_depth
                weight = (weight1 + weight2) / 2

        return weight


@dataclass(slots=True, frozen=True)
class node_levels(TaxonomyFunc, SupportsMetadata):
    """Node levels similarity measure of two nodes in a taxonomy.

    The similarity is calculated based on the levels of the nodes.

    Args:
        strategy: The strategy to use in case one of the node is the lowest common ancestor (lca).
            One of "optimistic", "pessimistic", or "average".

    ![node levels](../../../../assets/taxonomy/node-levels.png)

    Examples:
        >>> taxonomy = Taxonomy("./data/cars-taxonomy.yaml")
        >>> sim = node_levels("optimistic")
        >>> sim(taxonomy, "audi", "Volkswagen AG")
        1.0
        >>> sim(taxonomy, "audi", "bmw")
        0.3333333333333333
    """

    strategy: TaxonomyStrategy

    @override
    def __call__(self, taxonomy: Taxonomy, x: str, y: str) -> float:
        node1 = taxonomy.nodes[x]
        node2 = taxonomy.nodes[y]
        lca = taxonomy.lca(node1, node2)

        if self.strategy == "optimistic":
            return lca.level / min(node1.level, node2.level)
        elif self.strategy == "pessimistic":
            return lca.level / max(node1.level, node2.level)
        elif self.strategy == "average":
            return lca.level / ((node1.level + node2.level) / 2)
        else:
            return 0.0


@dataclass(slots=True, frozen=True)
class path_steps(TaxonomyFunc, SupportsMetadata):
    """Path steps similarity measure of two nodes in a taxonomy.

    The similarity is calculated based on the steps up and down from the lowest common ancestor (lca).

    Args:
        weight_up: The weight to use for the steps up.
        weight_down: The weight to use for the steps down.

    ![path steps](../../../../assets/taxonomy/path.png)

    Examples:
        >>> taxonomy = Taxonomy("./data/cars-taxonomy.yaml")
        >>> sim = path_steps()
        >>> sim(taxonomy, "audi", "Volkswagen AG")
        0.8333333333333334
        >>> sim(taxonomy, "audi", "bmw")
        0.3333333333333333
    """

    weight_up: float = 1.0
    weight_down: float = 1.0

    @override
    def __call__(self, taxonomy: Taxonomy, x: str, y: str) -> float:
        node1 = taxonomy.nodes[x]
        node2 = taxonomy.nodes[y]
        lca = taxonomy.lca(node1, node2)

        steps_up = node1.depth - lca.depth
        steps_down = node2.depth - lca.depth

        weighted_steps = (steps_up * self.weight_up) + (steps_down * self.weight_down)
        max_weighted_steps = (taxonomy.max_depth * self.weight_up) + (
            taxonomy.max_depth * self.weight_down
        )

        return (max_weighted_steps - weighted_steps) / max_weighted_steps


_taxonomy_func = wu_palmer()


@dataclass(slots=True)
class load(SimPairFunc[str, float], SupportsMetadata):
    """Load a taxonomy and return a function that measures the similarity.

    The taxonomy is loaded from the given path and expected to conform to the following structure:

    ```yaml
    name: ROOT
    weight: 0.0
    children:
      - name: CHILD1
        weight: 0.4
        children:
          - name: GRANDCHILD1
            weight: 0.8
            children:
              - name: GREATGRANDCHILD1
              - name: GREATGRANDCHILD2
          - name: GRANDCHILD2
      - name: CHILD2
        weight: 0.6
        children: []
    ```

    The `name` field is required for each node, and the `children` field is optional.
    The `weight` field is optional and can be used to assign a weight/similarity value to the node.
    If not set, the default value is 1.0.
    The `weight` is only used by the measure `user_weights` and ignored otherwise.

    Examples:
        >>> sim = load("./data/cars-taxonomy.yaml", measure=wu_palmer())
        >>> sim("audi", "porsche")
        0.5
        >>> sim("audi", "bmw")
        0.0
    """

    path: FilePath
    measure: TaxonomyFunc = _taxonomy_func
    taxonomy: Taxonomy = field(init=False)

    @property
    @override
    def metadata(self) -> JsonDict:
        return {
            "path": str(self.path),
            "measure": get_metadata(self.measure),
        }

    def __post_init__(self) -> None:
        self.taxonomy = Taxonomy(self.path)

    @override
    def __call__(self, x: str, y: str) -> float:
        return self.measure(self.taxonomy, x, y)
