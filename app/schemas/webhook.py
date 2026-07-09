import ipaddress
import socket
import re
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Prefixos IPv4/IPv6 privados, loopback, link-local e reservados
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),        # "This" network
    ipaddress.ip_network("10.0.0.0/8"),       # Private
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local
    ipaddress.ip_network("172.16.0.0/12"),    # Private
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),   # 6to4 Relay
    ipaddress.ip_network("192.168.0.0/16"),   # Private
    ipaddress.ip_network("198.18.0.0/15"),    # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("::/128"),           # IPv6 unspecified
    ipaddress.ip_network("fc00::/7"),         # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
    ipaddress.ip_network("ff00::/8"),         # IPv6 multicast
]


def _is_internal_host(hostname: str) -> bool:
    """Resolve o hostname e verifica se o IP é privado/reservado."""
    # Primeiro tenta como IP literal
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        return any(ip in net for net in _BLOCKED_NETWORKS)

    # Resolve DNS
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        # Não conseguiu resolver — permite (vai falhar no httpx depois)
        return False

    for family, _, _, _, sockaddr in resolved:
        addr = sockaddr[0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if any(ip in net for net in _BLOCKED_NETWORKS):
            return True
    return False


def validate_webhook_url(url: str) -> str:
    """Valida a URL do webhook: scheme seguro e sem IPs internos."""
    parsed = urlparse(url)

    if parsed.scheme not in ("https", "http"):
        raise ValueError("URL deve usar scheme https:// ou http://")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL inválida: hostname ausente")

    if _is_internal_host(hostname):
        raise ValueError(f"URL aponta para endereço interno ou reservado: {hostname}")

    return url


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=500)
    event: str = Field(..., pattern="^(new_message|peak_engagement|sentiment_change)$")

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        return validate_webhook_url(v)


class WebhookResponse(BaseModel):
    id: int
    user_id: int
    url: str
    event: str
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
