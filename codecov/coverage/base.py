import dataclasses
import decimal
import json
import pathlib
from abc import ABC, abstractmethod
from typing import Any

from codecov.config import Config, TestFramework
from codecov.exceptions import ConfigurationException
from codecov.log import log

COVERAGE_HANDLER_REGISTRY: dict[TestFramework, type['BaseCoverageHandler']] = {}


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


class BaseCoverageHandler(ABC):
    TEST_FRAMEWORK: TestFramework

    def __init_subclass__(cls) -> None:
        COVERAGE_HANDLER_REGISTRY[cls.TEST_FRAMEWORK] = cls
        super().__init_subclass__()

    def convert_to_decimal(self, value: float | decimal.Decimal, precision: int = 2) -> decimal.Decimal:
        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(float(value) / 100))
        return value.quantize(
            exp=decimal.Decimal(10) ** -precision,
            rounding=decimal.ROUND_DOWN,
        )

    # TODO: Fix the typing and rename this to get_coverage_json
    def get_coverage_info(self, coverage_path: pathlib.Path) -> Any:
        try:
            with coverage_path.open() as coverage_data:
                json_coverage = json.loads(coverage_data.read())
        except FileNotFoundError as exc:
            log.error('Coverage report file not found at the specified location: %s', coverage_path)
            raise ConfigurationException from exc
        except json.JSONDecodeError as exc:
            log.error('Invalid JSON format in coverage report file: %s', coverage_path)
            raise ConfigurationException from exc

        # TODO: Move the below code to a separate function
        try:
            return self.extract_info(data=json_coverage)
        except KeyError as exc:
            log.error('Unable to extract coverage info from coverage report file: %s', coverage_path)
            raise ConfigurationException from exc

    @abstractmethod
    def extract_info(self, data: dict) -> Any:
        raise NotImplementedError  # pragma: no cover

    def get_coverage(self, config: Config) -> Any:
        return self.get_coverage_info(coverage_path=config.COVERAGE_PATH)

    @abstractmethod
    def get_diff_coverage(
        self,
        added_lines: dict[pathlib.Path, list[int]],
        coverage: Any,
        config: Config,
    ) -> DiffCoverage:
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def get_coverage_handler(cls, test_framework: TestFramework) -> type['BaseCoverageHandler']:
        try:
            return COVERAGE_HANDLER_REGISTRY[test_framework]
        except KeyError as exc:
            log.error('No coverage handler found for test framework: %s', test_framework.value)
            raise ConfigurationException from exc
