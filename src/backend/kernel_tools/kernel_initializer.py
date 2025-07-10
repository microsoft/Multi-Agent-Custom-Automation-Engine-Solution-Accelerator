from semantic_kernel import Kernel
from semantic_kernel.core_plugins import TimePlugin

def create_kernel() -> Kernel:
    kernel = Kernel()
    kernel.import_plugin_from_object(TimePlugin(), plugin_name="time")
    return kernel
