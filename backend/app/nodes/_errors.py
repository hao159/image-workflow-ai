"""Node input validation error carrying a stable i18n code slug."""


class NodeInputError(ValueError):
    """ValueError with an attached stable error code for i18n.

    Raise this instead of plain ValueError in node run() methods so the engine
    can forward `code` and `params` into the RunEvent for the frontend to
    translate.
    """

    def __init__(self, message: str, code: str, params: dict | None = None):
        super().__init__(message)
        self.code = code
        self.params: dict = params or {}
