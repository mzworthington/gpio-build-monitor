#!/usr/bin/env python3

import json
import os
import re

import pytest
from aioresponses import aioresponses
from monitor.ci_gateway.constants import CiResult as Result
from monitor.ci_gateway.constants import IntegrationType
from monitor.ci_gateway.github import APIError, GitHubAction, github_security_payload, link_rel_next

os.environ['GITHUB_TOKEN'] = 'secret'

_RUNS_URL = re.compile(
    r'https://api\.github\.com/repos/super-man/awesome/actions/runs(\?.*)?'
)
_WORKFLOWS_URL = re.compile(
    r'https://api\.github\.com/repos/super-man/awesome/actions/workflows(\?.*)?'
)
_PULLS_URL = re.compile(
    r'https://api\.github\.com/repos/super-man/awesome/pulls(\?.*)?'
)
_DEPENDABOT_URL = re.compile(
    r'https://api\.github\.com/repos/super-man/awesome/dependabot/alerts(\?.*)?'
)
_CODEQL_URL = re.compile(
    r'https://api\.github\.com/repos/super-man/awesome/code-scanning/alerts(\?.*)?'
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
            m.get(_WORKFLOWS_URL, body='', status=403, repeat=True)
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

    @pytest.mark.asyncio
    async def test_retries_runs_without_auth_after_github_403(self):
        from aioresponses import CallbackResult

        workflows = {
            'workflows': [
                {
                    'id': 1001,
                    'name': 'CI',
                    'state': 'active',
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
            ]
        }

        def runs_cb(_url, **kwargs):
            headers = kwargs.get('headers') or {}
            if headers.get('Authorization'):
                return CallbackResult(
                    status=403,
                    payload={'message': 'API rate limit exceeded'},
                )
            return CallbackResult(status=200, payload=runs)

        import aiohttp
        with aioresponses() as m:
            m.get(_WORKFLOWS_URL, payload=workflows, status=200)
            m.get(_RUNS_URL, callback=runs_cb, repeat=True)
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                result = await action.get_latest(session)

        assert len(result) == 1
        assert result[0]['name'] == 'CI'
        assert result[0]['status'] == Result.PASS

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

    def test_omits_dependabot_version_update_runs(self):
        action = GitHubAction(
            username='super-man', repo='awesome', branch='*')
        runs = [
            {
                'id': 1,
                'name': 'CI',
                'head_branch': 'main',
                'created_at': '2020-01-04T00:00:00Z',
            },
            {
                'id': 2,
                'name': (
                    'npm_and_yarn in /infra/cloudflare for js-yaml'
                    ' - Update #1571184910'
                ),
                'head_branch': 'main',
                'created_at': '2020-01-05T00:00:00Z',
            },
        ]
        jobs = action.get_unique_latest_jobs(runs)
        assert [job['name'] for job in jobs] == ['CI']

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

    @pytest.mark.asyncio
    async def test_open_pull_requests_counts_ready_and_draft(self):
        import aiohttp
        with aioresponses() as m:
            m.get(
                _PULLS_URL,
                payload=[
                    {'number': 1, 'draft': False},
                    {'number': 2, 'draft': True},
                ],
                status=200,
            )
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                count, url = await action.open_pull_requests(session)
        assert count == 2
        assert url == 'https://github.com/super-man/awesome/pulls'

    @pytest.mark.asyncio
    async def test_open_pull_requests_returns_absent_on_error(self):
        import aiohttp
        with aioresponses() as m:
            m.get(_PULLS_URL, body='', status=500, repeat=True)
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                count, url = await action.open_pull_requests(session)
        assert count is None
        assert url is None

    @pytest.mark.asyncio
    async def test_security_findings_counts_dependabot_and_codeql(self):
        import aiohttp
        with aioresponses() as m:
            m.get(
                _DEPENDABOT_URL,
                payload=[{'number': 1}, {'number': 2}],
                status=200,
            )
            m.get(
                _CODEQL_URL,
                payload=[{'number': 9}],
                status=200,
            )
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                findings = await action.security_findings(session)
        assert findings == github_security_payload(
            'super-man',
            'awesome',
            vulnerabilities=2,
            codeql=1,
        )
        assert findings['count'] == 3
        assert findings['vulnerabilities']['items'] == []
        assert findings['codeql']['items'] == []

    @pytest.mark.asyncio
    async def test_security_findings_treats_missing_codeql_as_zero(self):
        import aiohttp
        with aioresponses() as m:
            m.get(_DEPENDABOT_URL, payload=[{'number': 4}], status=200)
            m.get(_CODEQL_URL, payload={'message': 'no analysis found'}, status=404)
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                findings = await action.security_findings(session)
        assert findings['count'] == 1
        assert findings['vulnerabilities']['count'] == 1
        assert findings['codeql']['count'] == 0

    @pytest.mark.asyncio
    async def test_security_findings_absent_when_both_forbidden(self):
        import aiohttp
        with aioresponses() as m:
            m.get(_DEPENDABOT_URL, payload={'message': 'Forbidden'}, status=403)
            m.get(_CODEQL_URL, payload={'message': 'Forbidden'}, status=403)
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                findings = await action.security_findings(session)
        assert findings is None

    @pytest.mark.asyncio
    async def test_security_findings_follows_next_link(self):
        import aiohttp
        next_url = (
            'https://api.github.com/repos/super-man/awesome/dependabot/alerts'
            '?state=open&per_page=100&page=2'
        )
        with aioresponses() as m:
            m.get(
                _DEPENDABOT_URL,
                payload=[{'number': 1}],
                status=200,
                headers={'Link': f'<{next_url}>; rel="next"'},
            )
            m.get(next_url, payload=[{'number': 2}, {'number': 3}], status=200)
            m.get(_CODEQL_URL, payload=[], status=200)
            action = GitHubAction(username='super-man', repo='awesome')
            async with aiohttp.ClientSession() as session:
                findings = await action.security_findings(session)
        assert findings['vulnerabilities']['count'] == 3
        assert findings['count'] == 3

    @pytest.mark.asyncio
    async def test_security_findings_absent_without_token(self, monkeypatch):
        monkeypatch.delenv('GITHUB_TOKEN', raising=False)
        import aiohttp
        action = GitHubAction(username='super-man', repo='awesome', token=None)
        async with aiohttp.ClientSession() as session:
            assert await action.security_findings(session) is None

    def test_link_rel_next_reads_github_header(self):
        header = (
            '<https://api.github.com/repos/a/b/dependabot/alerts?page=2>; rel="next", '
            '<https://api.github.com/repos/a/b/dependabot/alerts?page=4>; rel="last"'
        )
        assert link_rel_next(header).endswith('page=2')
        assert link_rel_next(None) is None

    def test_github_action_init_has_no_kwargs_bag(self):
        import inspect

        kinds = [
            param.kind
            for param in inspect.signature(GitHubAction.__init__).parameters.values()
        ]
        assert inspect.Parameter.VAR_KEYWORD not in kinds
