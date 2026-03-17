class BusinessRuleError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class PayloadValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("Payload inválido")
