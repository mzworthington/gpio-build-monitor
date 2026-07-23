#!/usr/bin/env python3

import json
import os
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses

from monitor.ci_gateway.circleci import API_BASE, APIError, CircleCI
from monitor.ci_gateway.constants import CiResult as Result
from monitor.ci_gateway.constants import IntegrationType

os.environ['CIRCLE_CI_TOKEN'] = 'secret'
FIXTURE_DIR = Path(__file__).parent


class TestCircleCi:
    def test_type(self):
        assert IntegrationType.CIRCLECI == CircleCI(**{
            'username': 'super-man',
            'repo': 'awesome'}).get_type()

    def test_map_result(self):
        latest = {
            "id": "wf-1234",
            "name": "blah",
            "status": "success",
            "created_at": "2020-12-28T09:23:57Z",
        }
        result = CircleCI.map_result(latest, "http://superurl.com")
        assert result["type"] == IntegrationType.CIRCLECI
        assert result["status"] == Result.PASS
        assert result["start"] == "2020-12-28T09:23:57Z"
        assert result["name"] == "blah"
        assert result["vcs"] == "http://superurl.com"
        assert result["id"] == "wf-1234"

    def test_running(self):
        latest = {
            "id": "wf-1234",
            "name": "blah",
            "status": "running",
            "created_at": "2020-12-28T09:23:57Z",
        }
        result = CircleCI.map_result(latest, "http://superurl.com")
        assert result["status"] == Result.RUNNING

    def test_pass(self):
        latest = {
            "id": "wf-1234",
            "name": "blah",
            "status": "success",
            "created_at": "2020-12-28T09:23:57Z",
        }
        result = CircleCI.map_result(latest, "http://superurl.com")
        assert result["status"] == Result.PASS

    def test_failed(self):
        latest = {
            "id": "wf-1234",
            "name": "blah",
            "status": "failed",
            "created_at": "2020-12-28T09:23:57Z",
        }
        result = CircleCI.map_result(latest, "http://superurl.com")
        assert result["status"] == Result.FAIL

    @pytest.mark.asyncio
    async def test_gets_latest_from_circle(self):
        with open(FIXTURE_DIR / 'circleci_pipelines.json') as pipelines_file:
            pipelines = json.load(pipelines_file)
        with open(FIXTURE_DIR / 'circleci_workflows.json') as workflows_file:
            workflows = json.load(workflows_file)

        pipelines_url = f"{API_BASE}/project/gh/super-man/awesome/pipeline"
        workflows_url = f"{API_BASE}/pipeline/pipe-1/workflow"

        with aioresponses() as m:
            m.get(pipelines_url, payload=pipelines, status=200)
            m.get(workflows_url, payload=workflows, status=200)

            action = CircleCI(**{'username': 'super-man',
                                 'repo': 'awesome'})
            async with aiohttp.ClientSession() as session:
                result = await action.get_latest(session)

        assert result[0]["type"] == IntegrationType.CIRCLECI
        assert result[0]["status"] == Result.PASS
        assert result[0]["name"] == "build_and_test"

        assert result[1]["type"] == IntegrationType.CIRCLECI
        assert result[1]["status"] == Result.FAIL
        assert result[1]["name"] == "check_vulnerabilities"

        assert result[2]["type"] == IntegrationType.CIRCLECI
        assert result[2]["status"] == Result.PASS
        assert result[2]["name"] == "scan_for_vulnerabilities"

    @pytest.mark.asyncio
    async def test_ignores_excluded_repo(self):
        with open(FIXTURE_DIR / 'circleci_pipelines.json') as pipelines_file:
            pipelines = json.load(pipelines_file)
        with open(FIXTURE_DIR / 'circleci_workflows.json') as workflows_file:
            workflows = json.load(workflows_file)

        pipelines_url = f"{API_BASE}/project/gh/super-man/awesome/pipeline"
        workflows_url = f"{API_BASE}/pipeline/pipe-1/workflow"

        with aioresponses() as m:
            m.get(pipelines_url, payload=pipelines, status=200)
            m.get(workflows_url, payload=workflows, status=200)

            action = CircleCI(**{'username': 'super-man',
                                 'repo': 'awesome',
                                 'excluded_workflows': ['scan_for_vulnerabilities']})
            async with aiohttp.ClientSession() as session:
                result = await action.get_latest(session)

        assert result[0]["name"] == "build_and_test"
        assert result[1]["name"] == "check_vulnerabilities"
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_fails_when_not_200(self):
        pipelines_url = f"{API_BASE}/project/gh/super-man/awesome/pipeline"
        with aioresponses() as m:
            m.get(pipelines_url, status=400)
            action = CircleCI(**{'username': 'super-man',
                                 'repo': 'awesome'})
            async with aiohttp.ClientSession() as session:
                with pytest.raises(APIError) as excinfo:
                    await action.get_latest(session)

        assert str(excinfo.value) == (
            "APIError: GET "
            f"{pipelines_url} 400"
        )
