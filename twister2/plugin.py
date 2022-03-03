import logging
from pathlib import Path

import pytest

from twister2.report.test_plan_plugin import TestPlanPlugin
from twister2.yaml_file_parser import YamlFile

SAMPLE_FILENAME: str = 'sample.yaml'
TESTCASE_FILENAME: str = 'testcase.yaml'

logger = logging.getLogger(__name__)


def pytest_collect_file(parent, path):
    if path.basename in (SAMPLE_FILENAME, TESTCASE_FILENAME):
        return YamlFile.from_parent(parent, path=Path(path))


def pytest_addoption(parser: pytest.Parser):
    custom_reports = parser.getgroup('Twister reports')
    custom_reports.addoption(
        '--testplan',
        dest='testplan_path',
        metavar='path',
        action='store',
        default=None,
        help='generate csv containing test metadata'
    )


def pytest_configure(config: pytest.Config):
    # configure TestPlan plugin
    testplan_path = config.getoption('testplan_path')
    if testplan_path and not hasattr(config, 'workerinput'):
        config.pluginmanager.register(
            plugin=TestPlanPlugin(logfile=testplan_path, config=config),
            name='testplan'
        )
