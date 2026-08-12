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
_WORKFLOWS_URL = re.compile(
    r'https://api\.github\.com/repos/super-man/awesome/actions/workflows(\?.*)?'
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
        assert result["status"] == Result.WAITING

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

    def test_action_required_is_approval(self):
        latest = """{
            "id": 448533827,
            "status": "completed",
            "conclusion": "action_required",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "amazing-workflow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.APPROVAL

    def test_cancelled_is_ignored_as_pass(self):
        latest = """{
            "id": 448533827,
            "status": "completed",
            "conclusion": "cancelled",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "Pulumi"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.PASS

    def test_skipped_is_ignored_as_pass(self):
        latest = """{
            "id": 448533827,
            "status": "completed",
            "conclusion": "skipped",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "optional"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.PASS

    def test_timed_out_is_fail(self):
        latest = """{
            "id": 448533827,
            "status": "completed",
            "conclusion": "timed_out",
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "slow"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.FAIL

    def test_waiting_for_pipeline(self):
        latest = """{
            "id": 448533827,
            "status": "waiting",
            "conclusion": null,
            "created_at": "2020-12-28T09:23:57Z",
            "html_url": "http://super-thing.com",
            "name": "deploy"
        }"""
        result = GitHubAction.map_result(json.loads(latest))
        assert result["status"] == Result.WAITING

    @pytest.mark.asyncio
    async def test_gets_latest_from_git(self):
        fixture_dir = os.path.dirname(__file__)
        with open(os.path.join(fixture_dir, 'github_response.json')) as json_file:
            data = json.load(json_file)
        with open(
            os.path.join(fixture_dir, 'github_workflows_response.json')
        ) as json_file:
            workflows = json.load(json_file)

        import aiohttp
        with aioresponses() as m:
            m.get(_WORKFLOWS_URL, payload=workflows, status=200)
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
    async def test_skips_runs_for_deleted_workflows(self):
        """Runs for workflows without YAML (state=deleted) must not appear."""
        workflows = {
            'workflows': [
                {
                    'id': 1001,
                    'name': 'CI',
                    'path': '.github/workflows/ci.yml',
                    'state': 'active',
                },
                {
                    'id': 1002,
                    'name': 'Legacy',
                    'path': '.github/workflows/legacy.yml',
                    'state': 'deleted',
                },
            ]
        }
        runs = {
            'workflow_runs': [
                {
                    'id': 1,
                    'workflow_id': 1001,
                    'name': 'CI',
                    'html_url': 'https://example.com/ci',
                    'created_at': '2020-01-02T00:00:00Z',
                    'status': 'completed',
                    'conclusion': 'success',
                    'head_branch': 'main',
                },
                {
                    'id': 2,
                    'workflow_id': 1002,
                    'name': 'Legacy',
                    'html_url': 'https://example.com/legacy',
                    'created_at': '2020-01-03T00:00:00Z',
                    'status': 'completed',
                    'conclusion': 'failure',
                    'head_branch': 'main',
                },
            ]
        }

        import aiohttp
        with aioresponses() as m:
            m.get(_WORKFLOWS_URL, payload=workflows, status=200)
            m.get(_RUNS_URL, payload=runs, status=200)
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                result = await action.get_latest(session)

        assert len(result) == 1
        assert result[0]['name'] == 'CI'
        assert result[0]['status'] == Result.PASS

    @pytest.mark.asyncio
    async def test_fails_when_workflows_not_200(self):
        import aiohttp
        with aioresponses() as m:
            m.get(_WORKFLOWS_URL, body='', status=403)
            action = GitHubAction(**{'username': 'super-man',
                                     'repo': 'awesome'})
            async with aiohttp.ClientSession() as session:
                with pytest.raises(APIError) as excinfo:
                    await action.get_latest(session)

        msg = (
            "APIError: GET "
            "https://api.github.com/repos/super-man/awesome/actions/workflows 403"
        )
        assert str(excinfo.value) == msg

    @pytest.mark.asyncio
    async def test_fails_when_not_200(self):
        import aiohttp
        with aioresponses() as m:
            m.get(
                _WORKFLOWS_URL,
                payload={'workflows': [{'id': 1, 'state': 'active'}]},
                status=200,
            )
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

    def test_collapses_dependabot_update_ids_to_newest(self):
        """Dependabot names each check uniquely; keep one newest per ecosystem/dir."""
        action = GitHubAction(
            username='super-man', repo='awesome', branch='*')
        runs = [
            {
                'id': 10,
                'name': 'npm_and_yarn in /. - Update #100',
                'head_branch': 'main',
                'created_at': '2020-01-01T00:00:00Z',
                'status': 'completed',
                'conclusion': 'failure',
            },
            {
                'id': 20,
                'name': (
                    'npm_and_yarn in /. for lodash, undici - Update #200'
                ),
                'head_branch': 'main',
                'created_at': '2020-01-03T00:00:00Z',
                'status': 'completed',
                'conclusion': 'success',
            },
            {
                'id': 30,
                'name': 'npm_and_yarn in /app - Update #300',
                'head_branch': 'main',
                'created_at': '2020-01-02T00:00:00Z',
                'status': 'completed',
                'conclusion': 'success',
            },
            {
                'id': 1,
                'name': 'CI',
                'head_branch': 'main',
                'created_at': '2020-01-04T00:00:00Z',
                'status': 'completed',
                'conclusion': 'success',
            },
        ]
        jobs = action.get_unique_latest_jobs(runs)
        names = {job['name'] for job in jobs}
        assert names == {
            'CI',
            'npm_and_yarn in /. for lodash, undici - Update #200',
            'npm_and_yarn in /app - Update #300',
        }
        by_id = {job['id']: job for job in jobs}
        assert 10 not in by_id

    def test_picks_newest_created_at_within_stable_name(self):
        action = GitHubAction(
            username='super-man', repo='awesome', branch='*')
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
                'head_branch': 'main',
                'created_at': '2020-01-02T00:00:00Z',
            },
        ]
        jobs = action.get_unique_latest_jobs(runs)
        assert len(jobs) == 1
        assert jobs[0]['id'] == 2

    def test_workflow_identity_key_strips_update_noise(self):
        assert GitHubAction.workflow_identity_key('CI') == 'CI'
        assert (
            GitHubAction.workflow_identity_key(
                'npm_and_yarn in /. - Update #1514087283'
            )
            == 'npm_and_yarn in /.'
        )
        assert (
            GitHubAction.workflow_identity_key(
                'npm_and_yarn in /app for brace-expansion, undici - Update #9'
            )
            == 'npm_and_yarn in /app'
        )

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
