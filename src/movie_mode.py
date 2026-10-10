import os


class MovieMode:

    def __init__(self):

        self.host = os.getenv(
            "MOVIE_MODE_HOST"
        )

        self.port = int(
            os.getenv(
                "MOVIE_MODE_PORT",
                "8765"
            )
        )

        self.token = os.getenv(
            "MOVIE_MODE_TOKEN",
            ""
        )

        self.enabled = False
        self.last_result = None


    def configured(self):

        return bool(self.host)


    def set_enabled(self, pool, enabled):

        if not self.host:

            self.last_result = (
                "MOVIE_MODE_HOST is not configured"
            )

            return False, self.last_result


        action = "off" if enabled else "on"

        payload = (
            self.token
            + ":"
            + action
        ).encode("utf-8")

        sock = None


        try:

            sock = pool.socket(
                pool.AF_INET,
                pool.SOCK_DGRAM
            )

            bytes_sent = sock.sendto(
                payload,
                (
                    self.host,
                    self.port
                )
            )


            if bytes_sent != len(payload):

                raise OSError(
                    "Incomplete movie-mode command"
                )


            self.enabled = enabled
            self.last_result = action

            message = (
                "Movie mode on"
                if enabled
                else "Movie mode off"
            )

            print(message)

            return True, message


        except Exception as e:

            self.last_result = str(e)

            print(
                "Movie mode failed:",
                e
            )

            return False, str(e)


        finally:

            if sock is not None:

                try:

                    sock.close()

                except Exception:

                    pass


    def toggle(self, pool):

        return self.set_enabled(
            pool,
            not self.enabled
        )
