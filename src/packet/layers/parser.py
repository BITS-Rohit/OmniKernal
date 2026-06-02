from src.packet.contracts import IntentPacket, PacketState
from src.packet.interfaces import BaseLayer


class Parser(BaseLayer):
    async def process(self, packet: IntentPacket) -> IntentPacket:
        """
        Parses the sanitized_text to create cli based headers and vals and store in packet.

        Steps:
            1. Finds '--<CLI Name>'
            2. After that every text till next '--<CLI Name>' is considered as value.
            3. Store the cli args in the packet's message_cli_args field.
            4. If any cli arg is not found passes Empty dict().
        """
        if packet.sanitized_text is None:
            packet.logger.debug("Dropping packet due to no Sanitized Message found.")
            return packet

        packet.state = PacketState.PARSED

        text = packet.sanitized_text
        length = len(text)
        i = 0
        last_key = None
        while i < length:
            while i < length and text[i] == " ":
                i += 1
            if i >= length:
                break
            start = i
            while i < length and text[i] != " ":
                i += 1
            token = text[start:i]
            if token.startswith("--"):
                packet.message_cli_args[token] = ""
                last_key = token
            elif last_key is not None:
                if packet.message_cli_args[last_key]:
                    packet.message_cli_args[last_key] += " " + token
                else:
                    packet.message_cli_args[last_key] = token
        return packet
