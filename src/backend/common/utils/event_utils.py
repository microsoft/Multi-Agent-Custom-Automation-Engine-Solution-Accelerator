import logging

from azure.monitor.events.extension import track_event
from common.config.app_config import config


def track_event_if_configured(event_name: str, event_data: dict):
    """Track an event if Application Insights is configured.

    This function safely wraps the Azure Monitor track_event function
    to handle potential errors with the ProxyLogger.

    Args:
        event_name: The name of the event to track
        event_data: Dictionary of event data/dimensions
    """
    try:
        instrumentation_key = config.APPLICATIONINSIGHTS_CONNECTION_STRING
        if instrumentation_key:
            track_event(event_name, event_data)
        else:
            logging.warning(
                f"Skipping track_event for {event_name} as Application Insights is not configured"
            )
    except AttributeError as e:
        # Handle the 'ProxyLogger' object has no attribute 'resource' error
        logging.warning(f"ProxyLogger error in track_event: {e}")
    except Exception as e:
        # Catch any other exceptions to prevent them from bubbling up
        logging.warning(f"Error in track_event: {e}")
