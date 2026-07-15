class DomainError(Exception):
    """Base class for domain errors."""
    pass

class RequesterNotFoundError(DomainError):
    def __init__(self, requester_id: str):
        super().__init__(f"Requester with ID {requester_id} not found.")
        self.requester_id = requester_id

class RequesterServiceError(DomainError):
    def __init__(self, details: str = ""):
        super().__init__(f"Requester service error: {details}")