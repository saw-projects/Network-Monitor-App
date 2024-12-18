import time
from logger import Logger
from hive_message import HiveMessage
from message_queue import MessageQueue
from app_settings import AppSettings
from config_message import ConfigMessage
from hive_node_manager import HiveNodeManager
from typing import Dict


class ConfigManager:
    """
    ConfigManager manages the configuration for the Hive network.

    Attributes:
    ----------
    enable : bool
        A class-level flag to enable or disable the config manager.
    logger : Logger
        An instance of the Logger class for logging messages.
    hive_node_manager : HiveNodeManager
        Manages the nodes in the Hive network.
    outbound_message_queue : MessageQueue
        A queue for outbound messages.
    """

    enable: bool = True

    def __init__(self, hive_node_manager: HiveNodeManager, outbound_message_queue: MessageQueue):
        """
        Initializes a new instance of ConfigManager.

        Parameters:
        ----------
        hive_node_manager : HiveNodeManager
            Manages the nodes in the Hive network.
        outbound_message_queue : MessageQueue
            A queue for outbound messages.
        """
        self.logger: Logger = Logger()
        self.hive_node_manager: HiveNodeManager = hive_node_manager
        self.outbound_message_queue: MessageQueue = outbound_message_queue

        self.logger.debug("ConfigManager", "ConfigManager initialized...")

    def run(self) -> None:
        """
        Starts the config protocol by periodically sending config messages to all nodes in the network.
        """
        while True:
            if ConfigManager.enable:
                self.logger.debug("ConfigManager", "Running...")

                # get config info and send to all other nodes
                config_info: Dict[str, Dict[str, str]] = {
                    self.hive_node_manager.local_node.friendly_name: {
                        'config': self.hive_node_manager.local_config}
                }
                # send config update to all nodes
                recipient_nodes = self.hive_node_manager.get_all_live_nodes()
                for node in recipient_nodes:
                    if node:

                        config_message: ConfigMessage = ConfigMessage(
                            sender=self.hive_node_manager.local_node,
                            recipient=node,
                            config=config_info
                        )
                        new_hive_message: HiveMessage = HiveMessage(config_message)
                        # print(f"Testing {new_hive_message}")
                        self.outbound_message_queue.enqueue(new_hive_message)
                    else:
                        self.logger.debug("ConfigManager", "No live nodes found...")

            time.sleep(AppSettings.CONFIG_FREQUENCY_IN_SECONDS)

    def enable_config_protocol(self) -> None:
        """
        Enables the gossip protocol by setting the appropriate flag.
        """
        self.logger.debug("ConfigManager", "Enabling config protocol...")
        ConfigManager.enable = True

    def disable_config_protocol(self) -> None:
        """
        Disables the gossip protocol by setting the appropriate flag.
        """
        self.logger.debug("ConfigManager", "Disabling config protocol...")
        ConfigManager.enable = False
