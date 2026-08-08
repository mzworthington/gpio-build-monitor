#!/usr/bin/env python3

import json
import os
import re

import pytest
from aioresponses import aioresponses

from monitor.ci_gateway.constants import CiResult as Result
from monitor.ci_gateway.constants import IntegrationType
from monitor.ci_gateway.github import APIError, GitHubAction

os.environ['GITHUB_TOKEN'] = 'secret'

_RUNS_URL = re.compile(
    r'https://api\.github\.com/repos/super-man/awesome/actions/runs(\?.*)?'
)


class TestGithub:
    def test_type(self):
        assert IntegrationType.GITHUB == GitHubAction(**{
            'username': 'super-man',
            'repo': 'awesome'}).get_type()

    def test_map_result(self):
        latest = """{
            "id": 448533827,
            "status": "completed",
            "conclusion": "success",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["type"] == IntegrationType.GITHUB
        assert result["status"] == Result.PASS
        assert result["start"] == "2020-12-28T09:23:57Z"
        assert result["id"] == 448533827
        assert result["name"] == "amazing-workflow"
        assert result["vcs"] == "http://super-thing.com"

    def test_running(self):
        latest = """{
            "id": 448533827,
            "status": "in_progress",
            "conclusion": null,
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.RUNNING

    def test_queued(self):
        latest = """{
            "id": 448533827,
            "status": "queued",
            "conclusion": null,
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.RUNNING

    def test_pass(self):
        latest = """{
            "id": 448533827,
            "status": "completed",
            "conclusion": "success",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.PASS

    def test_failed(self):
        latest = """{
            "id": 448533827,
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.FAIL

    def test_unknown_not_completed(self):
        latest = """{
            "id": 448533827,
            "status": "something",
            "conclusion": null,
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.UNKNOWN

    def test_unknown_completed(self):
        latest = """{
            "id": 448533827,
            "status": "something",
            "conclusion": "completed",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.UNKNOWN

    @pytest.mark.asyncio
    async def test_gets_latest_from_git(self):
        response_json = os.path.join(
            os.path.dirname(__file__),
            'github_response.json')
        with open(response_json) as json_file:
            data = json.load(json_file)

        import aiohttp
        with aioresponses() as m:
            m.get(_RUNS_URL, payload=data, status=200)

            action = GitHubAction(**{'username': 'super-man',
                                     'repo': 'awesome'})
            async with aiohttp.ClientSession() as session:
                result = await action.get_latest(session)

        assert result[0]["type"] == IntegrationType.GITHUB
        assert result[0]["name"] == "CI"
        assert result[0]["vcs"] == (
            "https://github.com/worthington10TW/gpio-build-monitor/actions/runs/448533827")
        assert result[0]["status"] == Result.FAIL

    @pytest.mark.asyncio
    async def test_fails_when_not_200(self):
        import aiohttp
        with aioresponses() as m:
            m.get(_RUNS_URL, body='', status=400)
            action = GitHubAction(**{'username': 'super-man',
                                     'repo': 'awesome'})
            async with aiohttp.ClientSession() as session:
                with pytest.raises(APIError) as excinfo:
                    await action.get_latest(session)

        msg = "APIError: GET https://api.github.com/repos/super-man/awesome/actions/runs 400"
        assert str(excinfo.value) == msg

    def test_filters_other_head_branches(self):
        action = GitHubAction(
            username='super-man', repo='awesome', branch='main')
        runs = [
            {
                'id': 1,
                'name': 'CI',
                'head_branch': 'main',
                'created_at': '2020-01-01T00:00:00Z',
            },
            {
                'id': 2,
                'name': 'CI',
                'head_branch': 'dependabot/npm_and_yarn/foo',
                'created_at': '2020-01-02T00:00:00Z',
            },
        ]
        jobs = action.get_unique_latest_jobs(runs)
        assert len(jobs) == 1
        assert jobs[0]['id'] == 1

    def test_excluded_workflow_patterns(self):
        action = GitHubAction(
            username='super-man',
            repo='awesome',
            branch='*',
            excluded_workflow_patterns=['* - Update #*'],
        )
        runs = [
            {
                'id': 1,
                'name': 'CI',
                'head_branch': 'main',
                'created_at': '2020-01-01T00:00:00Z',
            },
            {
                'id': 2,
                'name': 'npm_and_yarn in /. for lodash - Update #123',
                'head_branch': 'dependabot/npm_and_yarn/lodash',
                'created_at': '2020-01-02T00:00:00Z',
            },
        ]
        jobs = action.get_unique_latest_jobs(runs)
        assert len(jobs) == 1
        assert jobs[0]['name'] == 'CI'

    def test_all_branches_skips_head_filter(self):
        action = GitHubAction(
            username='super-man', repo='awesome', branch='*')
        runs = [
            {
                'id': 1,
                'name': 'CI',
                'head_branch': 'feature/x',
                'created_at': '2020-01-01T00:00:00Z',
            },
        ]
        jobs = action.get_unique_latest_jobs(runs)
        assert len(jobs) == 1
