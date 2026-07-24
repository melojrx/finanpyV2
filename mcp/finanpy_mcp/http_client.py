"""HTTP client for FinanPy DRF API."""
import httpx

from .sanitization import sanitize_payload


class FinanPyMCPError(Exception):
    """Safe error for FinanPy API failures."""


class FinanPyClient:
    """Thin httpx wrapper with Bearer auth, timeout and error normalization."""

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._timeout = timeout
        self._transport = transport

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        """Make an HTTP request and return parsed JSON. Raises FinanPyMCPError on failure."""
        url = f"{self.base_url}/{path.lstrip('/')}"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Hermes/FinanPyMCP 1.1",
        }
        if json is not None:
            headers["Content-Type"] = "application/json"

        try:
            with httpx.Client(
                timeout=self._timeout,
                headers=headers,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.request(method, url, params=params, json=json)
        except httpx.TimeoutException:
            raise FinanPyMCPError("Tempo esgotado ao consultar a API do FinanPy.")
        except httpx.RequestError:
            raise FinanPyMCPError("Falha de comunicação ao consultar a API do FinanPy.")

        try:
            payload = response.json()
        except Exception:
            raise FinanPyMCPError("Resposta não-JSON recebida da API do FinanPy.")

        if response.status_code == 401:
            raise FinanPyMCPError("Token FinanPy inválido ou expirado.")
        if response.status_code == 404:
            raise FinanPyMCPError("Recurso FinanPy não encontrado.")
        if response.status_code >= 400:
            detail = ""
            if isinstance(payload, dict):
                detail = str(payload.get("detail") or payload)
            detail = sanitize_payload({"d": detail})["d"]
            if response.status_code == 400:
                raise FinanPyMCPError(f"FinanPy rejeitou a operação: {detail}")
            raise FinanPyMCPError(
                f"FinanPy API erro HTTP {response.status_code}: {detail}"
            )

        return payload