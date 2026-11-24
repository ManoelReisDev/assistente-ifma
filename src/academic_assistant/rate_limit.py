"""Limites de consultas web em janelas fixas, compartilhados via SQLite local."""

from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address, IPv6Address
import os
from pathlib import Path
import sqlite3
import time


class RateLimitStorageError(RuntimeError):
    """Não é seguro liberar uma consulta sem contabilizá-la."""


@dataclass(frozen=True)
class RateLimitSettings:
    database: Path
    ip_minute: int = 5
    ip_day: int = 20
    global_minute: int = 10
    global_day: int = 100

    def __post_init__(self) -> None:
        for name in ("ip_minute", "ip_day", "global_minute", "global_day"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} deve ser um inteiro positivo.")

    @classmethod
    def from_env(cls, default_database: Path) -> "RateLimitSettings":
        values = {}
        for name in ("ip_minute", "ip_day", "global_minute", "global_day"):
            variable = f"WEB_RATE_LIMIT_{name.upper()}"
            if variable in os.environ:
                try:
                    values[name] = int(os.environ[variable])
                except ValueError as error:
                    raise ValueError(f"{variable} deve ser um inteiro positivo.") from error
        database = os.environ.get("WEB_RATE_LIMIT_DB", str(default_database)).strip()
        if not database:
            raise ValueError("WEB_RATE_LIMIT_DB não pode ser vazio.")
        return cls(database=Path(database), **values)


class RateLimiter:
    def __init__(
        self, settings: RateLimitSettings, *, clock: Callable[[], float] = time.time
    ) -> None:
        self.settings = settings
        self.clock = clock

    def consume(self, client: str) -> int:
        """Reserva uma consulta ou retorna segundos até todas as janelas liberarem."""
        try:
            address = ip_address(client)
            if isinstance(address, IPv6Address) and address.ipv4_mapped:
                address = address.ipv4_mapped
            client = address.compressed
        except ValueError:
            # Ausência de IP ou cliente sintético compartilham uma chave conservadora.
            pass
        client_key = "ip:" + sha256(client.encode("utf-8")).hexdigest()
        now = int(self.clock())
        rules = [
            (client_key, 60, self.settings.ip_minute),
            (client_key, 86_400, self.settings.ip_day),
            ("global", 60, self.settings.global_minute),
            ("global", 86_400, self.settings.global_day),
        ]
        try:
            self.settings.database.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.settings.database, timeout=5)) as db:
                # Leitura e incremento indivisíveis, inclusive entre workers no mesmo disco.
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS rate_limits ("
                    "client TEXT NOT NULL, window INTEGER NOT NULL, "
                    "start INTEGER NOT NULL, count INTEGER NOT NULL, "
                    "PRIMARY KEY (client, window, start))"
                )
                db.execute("DELETE FROM rate_limits WHERE start + window <= ?", (now,))
                retry_after = 0
                windows = []
                for key, window, limit in rules:
                    start = now // window * window
                    row = db.execute(
                        "SELECT count FROM rate_limits WHERE client=? AND window=? AND start=?",
                        (key, window, start),
                    ).fetchone()
                    if row and row[0] >= limit:
                        retry_after = max(retry_after, start + window - now)
                    windows.append((key, window, start))
                if retry_after:
                    db.rollback()
                    return retry_after
                db.executemany(
                    "INSERT INTO rate_limits (client, window, start, count) VALUES (?, ?, ?, 1) "
                    "ON CONFLICT (client, window, start) DO UPDATE SET count=count+1",
                    windows,
                )
                db.commit()
        except (OSError, sqlite3.Error) as error:
            raise RateLimitStorageError("Não foi possível contabilizar a consulta.") from error
        return 0
