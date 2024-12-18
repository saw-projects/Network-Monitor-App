from base_message import BaseMessage
from hive_node import HiveNode
from typing import Dict


class ConfigMessage(BaseMessage):
    """
    GossipMessage represents a message for gossip protocol in the Hive network.

    Attributes:
    ----------
    sender : HiveNode
        The sender node of the message.
    recipient : HiveNode
        The recipient node of the message.
    config : Dict[str, dict]
        A dictionary containing information about configs in the network.
    """

    def __init__(self, sender: HiveNode, recipient: HiveNode, config: Dict[str, dict]):
        """
        Initializes a new instance of ConfigMessage.

        Parameters:
        ----------
        sender : HiveNode
            The sender node of the message.
        recipient : HiveNode
            The recipient node of the message.
        config : Dict[str, dict]
            A dictionary containing information about configs in the network.
        """
        super().__init__(sender, recipient, 'config')
        self.config: Dict[str, dict] = config

    def to_dict(self) -> Dict[str, dict]:
        """
        Converts the ConfigMessage instance to a dictionary representation.

        Returns:
        -------
        Dict[str, dict]
            A dictionary representing the GossipMessage instance.
        """
        base_dict: Dict[str, dict] = super().to_dict()
        base_dict.update({'config': self.config})
        return base_dict
