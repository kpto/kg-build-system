"""Entry point for inspecting the demonstration declarations."""

import json

from demo.binding import BINDINGS
from demo.topology import TOPOLOGY


def main() -> None:
    """Print the portable topology and binding declarations."""
    print(
        json.dumps(
            {"topology": TOPOLOGY.to_dict(), "bindings": BINDINGS.to_dict()},
            indent=2,
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
