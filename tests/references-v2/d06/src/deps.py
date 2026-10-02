import heapq


class CycleError(Exception):
    def __init__(self, cycle):
        super().__init__(" -> ".join(cycle))
        self.cycle = cycle


def _find_cycle(graph):
    color = {}
    for start in sorted(graph):
        stack = [(start, iter(sorted(graph[start])))]
        path = [start]
        color[start] = 1
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = 2
                stack.pop(); path.pop()
                continue
            if color.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            if nxt not in color:
                color[nxt] = 1
                stack.append((nxt, iter(sorted(graph.get(nxt, [])))))
                path.append(nxt)
    return None


def build_order(deps: dict) -> list:
    graph = {k: list(v) for k, v in deps.items()}
    for v in deps.values():
        for d in v:
            graph.setdefault(d, [])
    cyc = _find_cycle(graph)
    if cyc:
        raise CycleError(cyc)
    indeg = {n: len(set(ds)) for n, ds in graph.items()}
    users = {n: [] for n in graph}
    for n, ds in graph.items():
        for d in set(ds):
            users[d].append(n)
    ready = [n for n, k in indeg.items() if k == 0]
    heapq.heapify(ready)
    out = []
    while ready:
        n = heapq.heappop(ready)
        out.append(n)
        for u in users[n]:
            indeg[u] -= 1
            if indeg[u] == 0:
                heapq.heappush(ready, u)
    return out
