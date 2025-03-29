class CoreBaseException(Exception):
    pass


class ConfigurationException(CoreBaseException):
    pass


class CoreProcessingException(CoreBaseException):
    pass


class GithubBaseException(CoreBaseException):
    pass


class CannotGetUser(GithubBaseException):
    pass


class CannotGetBranch(GithubBaseException):
    pass


class CannotPostComment(GithubBaseException):
    pass


class CannotGetPullRequest(GithubBaseException):
    pass


class ApiError(GithubBaseException):
    pass


class NotFound(ApiError):
    pass


class Unauthorized(ApiError):
    pass


class Forbidden(ApiError):
    pass


class Conflict(ApiError):
    pass


class ValidationFailed(ApiError):
    pass


class MissingEnvironmentVariable(ConfigurationException):
    pass


class TemplateBaseException(CoreBaseException):
    pass


class MissingMarker(TemplateBaseException):
    pass


class TemplateException(TemplateBaseException):
    pass
