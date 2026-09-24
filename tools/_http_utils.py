"""
_http_utils — HTTP 安全校验共享代码。
供 http_get / http_download 内部使用，不作为独立工具暴露。
"""

import ipaddress
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse


class SsrfBlocked(urllib.error.URLError):
    """SSRF 重定向拦截专用异常——调用方按类型识别，不依赖消息文案。"""

_PRIVATE_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]


def _blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    """Return whether an address is unsuitable as an outbound HTTP target."""
    if any(ip in net for net in _PRIVATE_NETS):
        return True
    # Catch loopback, unspecified, link-local, multicast and reserved ranges
    # that are not all represented consistently across Python versions.
    if any(getattr(ip, attr, False) for attr in ("is_loopback", "is_unspecified", "is_link_local", "is_multicast", "is_reserved")):
        return True
    mapped = getattr(ip, "ipv4_mapped", None)
    return bool(mapped and _blocked_ip(mapped))


def validate_url(url: str) -> dict | None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {
            "ok": False,
            "error": f"不支持的协议: {parsed.scheme}，仅允许 http/https",
        }
    hostname = parsed.hostname
    if not hostname:
        return {"ok": False, "error": "URL 缺少有效主机名"}
    try:
        ip = ipaddress.ip_address(hostname)
        if _blocked_ip(ip):
            return {"ok": False, "error": f"禁止访问内网地址: {hostname}"}
    except (AttributeError, ValueError):
        pass
    try:
        addrs = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for addr in addrs:
            ip_str = addr[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if _blocked_ip(ip):
                    return {
                        "ok": False,
                        "error": f"禁止访问内网地址: {hostname} 解析到 {ip_str}",
                    }
            except ValueError:
                pass
    except socket.gaierror:
        pass
    return None


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """每次 HTTP 重定向前重新走 SSRF 校验，防止 302→127.0.0.1 绕过。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        err = validate_url(newurl)
        if err:
            raise SsrfBlocked(f"重定向目标被拦截: {err['error']}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def make_opener():
    """创建带 SSRF 重定向校验的 URL opener。"""
    # Ignore HTTP(S)_PROXY/ALL_PROXY from the host environment.  A proxy can
    # make the validated destination differ from the actual socket target.
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}), SafeRedirectHandler()
    )


def check_url(url: str) -> dict | None:
    """SSRF 校验的便捷封装。"""
    return validate_url(url)
