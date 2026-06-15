import dataclasses
import decimal
import json
import pathlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from codecov.config import Config, TestFramework
from codecov.exceptions import ConfigurationException
from codecov.log import log

if TYPE_CHECKING:
    from codecov.coverage.jest import JestCoverage
    from codecov.coverage.pytest import PytestCoverage


@dataclasses.dataclass
class FileDiffCoverage:
    path: pathlib.Path
    percent_covered: decimal.Decimal
    covered_statements: list[int]
    missing_statements: list[int]
    added_statements: list[int]
    # Added lines tracks all the lines that were added in the diff, not just
    # the statements (so it includes comments, blank lines, etc.)
    added_lines: list[int]


@dataclasses.dataclass
class DiffCoverage:
    total_num_lines: int
    total_num_violations: int
    total_percent_covered: decimal.Decimal
    num_changed_lines: int
    files: dict[pathlib.Path, FileDiffCoverage]


class BaseCoverage:
    pass


T = TypeVar('T', bound=BaseCoverage)


class BaseCoverageHandler(ABC, Generic[T]):
    TEST_FRAMEWORK: TestFramework
    REGISTRY: ClassVar[dict[TestFramework, type['BaseCoverageHandler[Any]']]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        BaseCoverageHandler.REGISTRY[cls.TEST_FRAMEWORK] = cls

    def convert_to_decimal(self, value: float | decimal.Decimal, precision: int = 2) -> decimal.Decimal:
        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(float(value) / 100))
        return value.quantize(
            exp=decimal.Decimal(10) ** -precision,
            rounding=decimal.ROUND_DOWN,
        )

    def get_coverage(self, config: Config) -> T:
        coverage_path = config.COVERAGE_PATH
        try:
            with coverage_path.open() as coverage_data:
                json_coverage = json.loads(coverage_data.read())
        except FileNotFoundError as exc:
            log.error('Coverage report file not found at the specified location: %s', coverage_path)
            raise ConfigurationException from exc
        except json.JSONDecodeError as exc:
            log.error('Invalid JSON format in coverage report file: %s', coverage_path)
            raise ConfigurationException from exc

        try:
            return self.extract_info(data=json_coverage)
        except KeyError as exc:
            log.error('Unable to extract coverage info from coverage report file: %s', coverage_path)
            raise ConfigurationException from exc

    @abstractmethod
    def extract_info(self, data: dict) -> T:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def get_diff_coverage(
        self,
        added_lines: dict[pathlib.Path, list[int]],
        coverage: T,
        config: Config,
    ) -> DiffCoverage:
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def get_coverage_handler(
        cls,
        test_framework: TestFramework,
    ) -> 'BaseCoverageHandler[PytestCoverage | JestCoverage]':
        try:
            return cast(
                'BaseCoverageHandler[PytestCoverage | JestCoverage]',
                cls.REGISTRY[test_framework](),
            )
        except KeyError as exc:
            log.error('No coverage handler found for test framework: %s', test_framework.value)
            raise ConfigurationException from exc
