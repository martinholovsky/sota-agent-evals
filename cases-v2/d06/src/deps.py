class CycleError(Exception):
    def __init__(self, cycle):
        super().__init__(" -> ".join(cycle))
        self.cycle = cycle


def build_order(deps: dict) -> list:
    """deps maps a target to the list of targets it depends on (dependencies first).
    - Return every target (keys AND anything only mentioned as a dependency) in an order
      where each appears after all its dependencies.
    - Among targets that are ready at the same time, pick them in ALPHABETICAL order, so
      the result is deterministic.
    - On a cycle raise CycleError whose .cycle is the list of targets around the cycle with
      the first repeated at the end, e.g. ["a", "b", "a"]."""
    raise NotImplementedError
