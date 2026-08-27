import os


class WakeOnLan:

    def __init__(self):

        self.mac_address = os.getenv(
            "WOL_MAC_ADDRESS"
        )

        self.broadcast_address = os.getenv(
            "WOL_BROADCAST_ADDRESS",
            "255.255.255.255"
        )

        self.port = int(
            os.getenv(
                "WOL_PORT",
                "9"
            )
        )

        self.last_result = None


    def configured(self):

        return bool(self.mac_address)


    def magic_packet(self):

        if not self.mac_address:

            raise ValueError(
                "WOL_MAC_ADDRESS is not configured"
            )


        normalized = self.mac_address.replace(
            ":",
            ""
        ).replace(
            "-",
            ""
        ).replace(
            ".",
            ""
        )


        if len(normalized) != 12:

            raise ValueError(
                "WOL_MAC_ADDRESS must contain 12 hexadecimal digits"
            )


        try:

            mac = bytearray(
                int(
                    normalized[index:index + 2],
                    16
                )
                for index in range(0, 12, 2)
            )

        except ValueError:

            raise ValueError(
                "WOL_MAC_ADDRESS must contain only hexadecimal digits"
            )


        packet = bytearray(
            [255] * 6
        )

        packet.extend(
            mac * 16
        )

        return packet


    def send(self, pool):

        sock = None


        try:

            packet = self.magic_packet()

            sock = pool.socket(
                pool.AF_INET,
                pool.SOCK_DGRAM
            )

            sock.setsockopt(
                pool.SOL_SOCKET,
                pool.SO_BROADCAST,
                1
            )

            sock.sendto(
                packet,
                (
                    self.broadcast_address,
                    self.port
                )
            )

            self.last_result = "sent"

            print(
                "Wake-on-LAN packet sent to",
                self.mac_address
            )

            return True, "Wake-on-LAN packet sent"


        except Exception as e:

            self.last_result = str(e)

            print(
                "Wake-on-LAN failed:",
                e
            )

            return False, str(e)


        finally:

            if sock is not None:

                try:

                    sock.close()

                except Exception:

                    pass
