class DebugGlobalAccess:
    """Class to manage global access to the Magentic orchestration manager."""

    _managers = []

    @classmethod
    def add_manager(cls, manager):
        """Add a new manager to the global list."""
        cls._managers.append(manager)

    @classmethod
    def get_managers(cls):
        """Get the list of all managers."""
        return cls._managers
