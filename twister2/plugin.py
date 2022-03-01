import logging
from pathlib import Path

import pytest

from twister2.yaml_file import YamlFile

from .report.test_plan_plugin import TestPlanPlugin

logger = logging.getLogger(__name__)


# @pytest.fixture(scope='module')
# def dut(request: pytest.FixtureRequest):
#     logger.info('Dut fixture...')
#     logger.info(request.config.args)
#     return dict(name='dut1')


def pytest_collect_file(parent, path):
    if path.basename in ("sample.yaml", 'testcase.yaml'):
        return YamlFile.from_parent(parent, path=Path(path))


def pytest_addoption(parser):
    custom_reports = parser.getgroup('Twister reports')
    custom_reports.addoption(
        '--testplan',
        dest='testplan_path',
        metavar='path',
        action='store',
        default=None,
        help='generate csv containing test metadata'
    )


def pytest_configure(config):
    # configure TestPlan plugin
    testplan_path = config.getoption('testplan_path')
    if testplan_path and not hasattr(config, 'workerinput'):
        config.pluginmanager.register(
            plugin=TestPlanPlugin(logfile=testplan_path, config=config),
            name='testplan'
        )
