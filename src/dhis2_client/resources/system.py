from .base import Resource


class System(Resource):
    def info(self) -> dict:
        return self._get("/api/system/info")
