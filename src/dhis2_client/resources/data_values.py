from typing import Any, Dict, Optional

from .base import Resource


class DataValues(Resource):
    """
    Data value helpers.

    - GET/DELETE use querystring shorthand: de, pe, ou, co?, ao?
    - POST uses DHIS2-compliant JSON body keys:
      dataElement, period, orgUnit, categoryOptionCombo, attributeOptionCombo?, value
    """

    # Single value (READ)
    def get(self, de: str, pe: str, ou: str, **kwargs) -> Dict[str, Any]:
        """
        GET /api/dataValues?de=...&pe=...&ou=...&co=...&ao=...
        kwargs may include: co (COC), ao (AOC)
        """
        params = {"de": de, "pe": pe, "ou": ou, **kwargs}
        return self._get("/api/dataValues", params=params)

    # Single value (CREATE/UPDATE)
    def set(
        self,
        de: str,
        pe: str,
        ou: str,
        value: str | int | float,
        *,
        co: Optional[str] = None,
        ao: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /api/dataValues with full JSON keys.

        Args:
            de: dataElement id
            pe: period (e.g. YYYYMM)
            ou: orgUnit id
            value: numeric/string value (will be stringified)
            co: categoryOptionCombo id (required on most servers)
            ao: attributeOptionCombo id (optional)
        """
        body: Dict[str, Any] = {
            "dataElement": de,
            "period": pe,
            "orgUnit": ou,
            "value": str(value),
        }
        if co:
            body["categoryOptionCombo"] = co
        if ao:
            body["attributeOptionCombo"] = ao

        return self._post("/api/dataValues", json=body)

    # Single value (DELETE)
    def delete(self, de: str, pe: str, ou: str, **kwargs) -> Dict[str, Any]:
        """
        DELETE /api/dataValues?de=...&pe=...&ou=...&co=...&ao=...
        kwargs may include: co (COC), ao (AOC)
        """
        params = {"de": de, "pe": pe, "ou": ou, **kwargs}
        return self._delete("/api/dataValues", params=params)

    # Data Value Sets (READ)
    def get_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        GET /api/dataValueSets?dataSet=...&orgUnit=...&period=...
        """
        return self._get("/api/dataValueSets", params=params)

    # Data Value Sets (CREATE/UPDATE)
    def post_set(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /api/dataValueSets with DHIS2-compliant payload:
        {
          "dataSet": "...",
          "orgUnit": "...",
          "period": "...",
          "dataValues": [
            {"dataElement":"...", "categoryOptionCombo":"...", "value":"..."}
          ]
        }
        """
        return self._post("/api/dataValueSets", json=payload)
