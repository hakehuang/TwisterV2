import logging
from pathlib import Path
import os

import pytest
from twister2.twister_config import TwisterConfig
from twister2.platform_specification import discover_platforms, validate_platforms_list
from twister2.report.test_plan_csv import CsvTestPlan
from twister2.report.test_plan_json import JsonTestPlan
from twister2.report.test_plan_plugin import TestPlanPlugin
from twister2.report.test_results_json import JsonResultsReport
from twister2.report.test_results_plugin import TestResultsPlugin
from twister2.yaml_file import YamlFile
from twister2.helper import configure_logging
from twister2.filter.filter_plugin import FilterPlugin

SAMPLE_FILENAME: str = 'sample.yaml'
TESTCASE_FILENAME: str = 'testcase.yaml'

logger = logging.getLogger(__name__)

# include fixtures
pytest_plugins = (
    'twister2.fixtures.builder',
    'twister2.fixtures.log_parser',
)


def pytest_collect_file(parent, path):
    # discovers all yaml tests in test directory
    if path.basename in (SAMPLE_FILENAME, TESTCASE_FILENAME):
        return YamlFile.from_parent(parent, path=Path(path))


def pytest_addoption(parser: pytest.Parser):
    custom_reports = parser.getgroup('Twister reports')
    custom_reports.addoption(
        '--testplan-csv',
        dest='testplan_csv_path',
        metavar='PATH',
        action='store',
        default=None,
        help='generate test plan in CSV format'
    )
    custom_reports.addoption(
        '--testplan-json',
        dest='testplan_json_path',
        metavar='PATH',
        action='store',
        default=None,
        help='generate test plan in JSON format'
    )
    custom_reports.addoption(
        '--results-json',
        dest='results_json_path',
        metavar='PATH',
        action='store',
        default=None,
        help='generate test results report in JSON format'
    )

    twister_group = parser.getgroup('Twister')
    twister_group.addoption(
        '--build-only',
        default=False,
        action='store_true',
        help='build only'
    )
    twister_group.addoption(
        '--platform',
        action='append',
        help='build tests for specific platforms'
    )
    twister_group.addoption(
        '--board-root',
        metavar='PATH',
        action='append',
        default=None,
        help='directory to search for board configuration files'
    )
    parser.addini(
        'board_root',
        type='pathlist',
        help='directories to search for Zephyr board configuration files',
    )
    twister_group.addoption(
        '--zephyr-base',
        metavar='path',
        action='store',
        default=None,
        help='base directory for Zephyr'
    )
    parser.addini(
        'zephyr_base',
        type='string',
        help='base directory for Zephyr',
    )
    twister_group.addoption(
        '--tags',
        action='append',
        help='filter test by tags, e.g.: --tags=@tag1,~@tag2 --tags=@tag3'
    )


def pytest_configure(config: pytest.Config):
    if config.getoption('help'):
        return

    zephyr_base = config.getoption('zephyr_base') or config.getini('zephyr_base') or os.environ.get('ZEPHYR_BASE')
    if not zephyr_base:
        pytest.exit(
            'Path to Zephyr directory must be provided as pytest argument or in environment variable: ZEPHYR_BASE'
        )

    worker_input = hasattr(config, 'workerinput')  # xdist worker

    configure_logging(config)

    # configure TestPlan plugin
    test_plan_writers = []
    if testplan_csv_path := config.getoption('testplan_csv_path'):
        test_plan_writers.append(CsvTestPlan(testplan_csv_path))
    if testplan_json_path := config.getoption('testplan_json_path'):
        test_plan_writers.append(JsonTestPlan(testplan_json_path))

    if test_plan_writers and not worker_input:
        config.pluginmanager.register(
            plugin=TestPlanPlugin(config=config, writers=test_plan_writers),
            name='testplan'
        )

    test_results_writers = []
    if test_result_json_path := config.getoption('results_json_path'):
        test_results_writers.append(JsonResultsReport(test_result_json_path))

    if test_results_writers and not worker_input and not config.option.collectonly:
        config.pluginmanager.register(
            plugin=TestResultsPlugin(config, writers=test_results_writers),
            name='test_results'
        )

    if config.getoption('tags') and not worker_input:
        config.pluginmanager.register(
            plugin=FilterPlugin(config),
            name='filter_tests'
        )

    logger.debug('ZEPHYR_BASE: %s', zephyr_base)

    config._platforms = get_platforms(config, zephyr_base)
    config.twister_config = TwisterConfig.create(config)

    # register custom markers for twister
    config.addinivalue_line(
        'markers', 'tags(tag1, tag2, ...): mark test for specific tags'
    )
    config.addinivalue_line(
        'markers', 'platform(platform_name): mark test for specific platform'
    )
    config.addinivalue_line(
        'markers', 'type(test_type): mark test for specific type'
    )


def get_platforms(config, zephyr_base) -> list:
    """Return list of platforms."""
    board_root_list = [
        f'{zephyr_base}/boards',
        f'{zephyr_base}/scripts/pylib/twister/boards',
    ]
    if board_root := (config.getoption('board_root') or config.getini('board_root')):
        board_root_list.extend(board_root)

    logger.debug('BOARD_ROOT_LIST: %s', board_root_list)

    platforms: list = []
    for directory in board_root_list:
        for platform_config in discover_platforms(Path(directory)):
            platforms.append(platform_config)
    validate_platforms_list(platforms)
    return platforms
