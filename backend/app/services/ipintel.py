"""Public-registry IP intelligence for an investigator-recorded IP.

NOT identity tracing: this only describes the recorded address itself
(version, scope, reverse DNS). WHO used it must come from VASP/ISP
records obtained through lawful process.
"""
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor


def _rdns(ip: str) -> str | None:
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(socket.gethostbyaddr, ip).result(timeout=4)[0]
    except Exception:
        return None


def ip_intel(ip: str) -> dict:
    if not ip:
        return {}
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return {"input": ip, "valid": False}
    info: dict = {"input": str(addr), "valid": True, "version": addr.version,
                  "is_private": addr.is_private, "is_global": addr.is_global,
                  "scope": "public" if addr.is_global else ("private" if addr.is_private else "special")}
    if addr.is_global:
        info["reverse_dns"] = _rdns(str(addr))
        info["note"] = ("Public-registry data only — describes the address, not the person. "
                        "Ownership/identity needs VASP or ISP records via lawful process.")
    else:
        info["reverse_dns"] = None
        info["note"] = ("Private/special range — not publicly routable. Correlate with the "
                        "source device/network log it was taken from.")
    return info
