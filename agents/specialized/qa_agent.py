# agents/specialized/qa_agent.py

import asyncio
import json
import logging
import os
import subprocess
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from uuid import uuid4

from ..base_agent import BaseAgent
from ..communication.protocol import AgentMessage


class QAAgent(BaseAgent):
    """
    QA Agent - Responsible for testing and validating code changes.
    """

    DEFAULT_CAPABILITIES = {
        "can_write_tests": True,
        "can_execute_tests": True,
        "can_report_bugs": True,
        "can_verify_fixes": True,
    }

    def __init__(self, **kwargs):
        """Initialize the QA Agent."""
        capabilities = self.DEFAULT_CAPABILITIES.copy()
        if "capabilities" in kwargs:
            capabilities.update(kwargs["capabilities"])
        kwargs["capabilities"] = capabilities

        # Let BaseAgent handle initialization via kwargs, including agent_type
        super().__init__(**kwargs)

        self.logger.info(f"QAAgent {self.agent_id} ({self.agent_name}) initialized.")
        # TODO: Specific initialization for QA Agent

    async def run_tests(
        self,
        test_paths: Optional[List[str]] = None,
        related_task_id: Optional[str] = None,
        commit_hash: Optional[str] = None,
        files_changed: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run tests and report results.
        Can be triggered by a code commit.
        """
        # If no specific tests provided, run all tests
        if not test_paths:
            test_paths = ["tests/"]

        # Log that we're starting tests
        await self.log_activity(
            activity_type="TestExecution",
            description=f"Running tests: {', '.join(test_paths)}",
            related_task_id=related_task_id,
            related_files=test_paths,
            input_data={
                "test_paths": test_paths,
                "commit_hash": commit_hash,
                "files_changed": files_changed,
            },
        )

        # Run pytest in a subprocess
        cmd = ["pytest", "-v"]
        cmd.extend(test_paths)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            stdout = result.stdout
            stderr = result.stderr
            return_code = result.returncode

            # Parse the test results
            test_results = self._parse_pytest_output(stdout)

            # Log the test results
            await self.log_activity(
                activity_type="TestResults",
                description=f"Test execution completed with return code {return_code}",
                related_task_id=related_task_id,
                related_files=test_paths,
                output_data={
                    "return_code": return_code,
                    "summary": test_results["summary"],
                    "failing_tests": test_results["failing_tests"],
                },
            )

            # If tests failed, analyze the failures
            if return_code != 0 and test_results["failing_tests"]:
                analysis = await self._analyze_test_failures(
                    test_results["failing_tests"]
                )

                # Log the analysis
                await self.log_activity(
                    activity_type="TestFailureAnalysis",
                    description=f"Analyzed {len(test_results['failing_tests'])} test failures",
                    related_task_id=related_task_id,
                    output_data={"analysis": analysis},
                )

                # Return results with analysis
                return {
                    "success": False,
                    "return_code": return_code,
                    "summary": test_results["summary"],
                    "failing_tests": test_results["failing_tests"],
                    "analysis": analysis,
                }

            # Return results
            return {
                "success": return_code == 0,
                "return_code": return_code,
                "summary": test_results["summary"],
                "failing_tests": test_results["failing_tests"],
            }

        except Exception as e:
            error_msg = f"Error running tests: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="TestExecutionError",
                description="Failed to run tests",
                related_task_id=related_task_id,
                related_files=test_paths,
                output_data={"error": str(e)},
            )

            return {"error": error_msg}

    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """
        Parse pytest output to extract test results.
        """
        # Extract summary line (e.g., "2 failed, 3 passed in 0.12s")
        summary_match = re.search(r"=+ (.+) in \d+\.\d+s =+", output)
        summary = summary_match.group(1) if summary_match else "Unknown result"

        # Extract failing tests
        failing_tests = []

        # Look for lines like "FAILED tests/test_api.py::test_create_item"
        failed_lines = re.finditer(r"FAILED (.+?)::(.+?)(\[.+])?\s", output)
        for match in failed_lines:
            file_path = match.group(1)
            test_name = match.group(2)

            # Find the error message for this test
            error_regex = (
                re.escape(f"{file_path}::{test_name}") + r".*?\n(.*?)(?:=|Captured|\Z)"
            )
            error_match = re.search(error_regex, output, re.DOTALL)
            error_msg = error_match.group(1).strip() if error_match else "Unknown error"

            failing_tests.append(
                {
                    "file_path": file_path,
                    "test_name": test_name,
                    "error_message": error_msg,
                }
            )

        return {"summary": summary, "failing_tests": failing_tests}

    async def _analyze_test_failures(
        self, failing_tests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze test failures to determine the root cause and possible solutions.
        """
        if not self.llm_provider:
            self.logger.warning(
                "No LLM provider available, skipping test failure analysis"
            )
            return []

        analyzed_failures = []

        for test in failing_tests:
            file_path = test["file_path"]
            test_name = test["test_name"]
            error_message = test["error_message"]

            # Read the test file
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    test_content = f.read()
            else:
                test_content = "File not found"

            # Find the implementation file being tested
            impl_file_path = self._guess_implementation_file(file_path)
            impl_content = "File not found"

            if impl_file_path and os.path.exists(impl_file_path):
                with open(impl_file_path, "r") as f:
                    impl_content = f.read()

            system_message = """You are a QA engineer analyzing a test failure.
            Based on the test file, implementation file, and error message,
            determine the most likely cause of the failure and suggest a solution.
            Provide your analysis in a clear, concise manner."""

            prompt = f"""
            I have a failing test with the following details:

            Test File: {file_path}
            Test Name: {test_name}
            Error Message: {error_message}

            Test File Content:
            ```python
            {test_content}
            ```

            Implementation File Content:
            ```python
            {impl_content}
            ```

            Please analyze this failure and provide:
            1. The root cause of the failure
            2. Which file needs to be modified (test or implementation)
            3. A suggested solution

            Format your response as JSON.
            """

            # Use the LLM to analyze the failure
            thought, error = await self.think(prompt, system_message)

            if error:
                self.logger.error(f"Error analyzing test failure: {error}")
                analysis = {
                    "file_path": file_path,
                    "test_name": test_name,
                    "error_message": error_message,
                    "analysis_error": error,
                }
            else:
                try:
                    # Extract JSON from the response
                    start_idx = thought.find("{")
                    end_idx = thought.rfind("}") + 1

                    if start_idx == -1 or end_idx == 0:
                        raise ValueError("No JSON object found in the response")

                    json_str = thought[start_idx:end_idx]
                    analysis_result = json.loads(json_str)

                    analysis = {
                        "file_path": file_path,
                        "test_name": test_name,
                        "error_message": error_message,
                        "root_cause": analysis_result.get("root_cause", "Unknown"),
                        "file_to_modify": analysis_result.get(
                            "file_to_modify", "Unknown"
                        ),
                        "suggested_solution": analysis_result.get(
                            "suggested_solution", "Unknown"
                        ),
                    }

                except (json.JSONDecodeError, ValueError) as e:
                    analysis = {
                        "file_path": file_path,
                        "test_name": test_name,
                        "error_message": error_message,
                        "parsing_error": str(e),
                        "raw_analysis": thought[:500],
                    }

            analyzed_failures.append(analysis)

        return analyzed_failures

    def _guess_implementation_file(self, test_file_path: str) -> Optional[str]:
        """
        Guess the implementation file path based on the test file path.
        """
        # Common patterns:
        # tests/test_api.py -> app/api.py
        # tests/api/test_users.py -> app/api/users.py

        # Remove 'tests/' prefix and 'test_' from filename
        if test_file_path.startswith("tests/"):
            file_path = test_file_path[6:]  # Remove 'tests/'
        else:
            file_path = test_file_path

        # Remove 'test_' prefix from filename
        file_path = re.sub(r"test_(.+\.py)", r"\1", file_path)

        # Check common app directory structures
        possible_paths = [
            os.path.join("app", file_path),
            os.path.join("src", file_path),
            file_path,
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    async def report_bug(
        self,
        title: str,
        description: str,
        steps_to_reproduce: List[str],
        expected_result: str,
        actual_result: str,
        severity: str = "Medium",
        assigned_to: Optional[str] = None,
        related_task_id: Optional[str] = None,
        related_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Report a bug discovered during testing.
        """
        if not self.db_client:
            self.logger.warning("No database client available, skipping bug report")
            return {"error": "No database connection available"}

        bug_id = str(uuid4())

        # Create the bug report
        query = """
        INSERT INTO artifacts (
            artifact_id, artifact_type, title, content,
            created_by, status, metadata, version
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING artifact_id
        """

        await self.db_client.execute(
            query,
            bug_id,
            "BugReport",
            title,
            description,
            self.agent_id,
            "OPEN",
            json.dumps(
                {
                    "steps_to_reproduce": steps_to_reproduce,
                    "expected_result": expected_result,
                    "actual_result": actual_result,
                    "severity": severity,
                    "assigned_to": assigned_to,
                    "related_task_id": related_task_id,
                    "related_files": related_files or [],
                }
            ),
            1,
        )

        # Log the bug report
        await self.log_activity(
            activity_type="BugReport",
            description=f"Bug reported: {title}",
            related_task_id=related_task_id,
            related_files=related_files or [],
            output_data={
                "bug_id": bug_id,
                "title": title,
                "severity": severity,
                "assigned_to": assigned_to,
            },
        )

        # Notify the assigned developer if specified
        if assigned_to:
            await self.send_message(
                receiver_id=assigned_to,
                content=f"Bug Report: {title}\n\n{description}\n\nSeverity: {severity}",
                message_type="BUG_REPORT",
                related_task_id=related_task_id,
                metadata={"bug_id": bug_id},
            )

        return {
            "success": True,
            "bug_id": bug_id,
            "title": title,
            "assigned_to": assigned_to,
        }

    async def handle_code_committed_message(self, message: AgentMessage):
        """Handles CODE_COMMITTED messages by triggering tests."""
        self.logger.info(
            f"Received CODE_COMMITTED message: {message.message_id} from {message.sender}"
        )

        commit_hash = message.metadata.get("commit_hash")
        files_changed = message.metadata.get("files_changed")
        related_task_id = message.related_task

        if not commit_hash:
            self.logger.warning(
                "CODE_COMMITTED message received without commit_hash in metadata."
            )
            # Optionally, send a REJECT message or log an error
            return

        await self.log_activity(
            activity_type="CodeCommitReceived",
            description=f"Received code commit notification. Commit: {commit_hash}",
            related_task_id=related_task_id,
            input_data=message.to_dict(),
        )

        # Trigger tests
        # For now, run_tests will use its default test_paths or those configured.
        # Future enhancement: Use files_changed to select specific tests.
        test_results = await self.run_tests(
            related_task_id=related_task_id,
            commit_hash=commit_hash,
            files_changed=files_changed,
        )

        # TODO: Based on test_results, potentially send BUG_REPORT or other follow-up messages.
        if test_results.get("success") is False and test_results.get("failing_tests"):
            self.logger.info(
                f"Tests failed for commit {commit_hash}. Further action may be needed."
            )
            # Example: await self.report_bug(...) or send message to BackendDeveloperAgent
        elif test_results.get("success") is True:
            self.logger.info(f"All tests passed for commit {commit_hash}.")
        else:
            self.logger.warning(
                f"Test execution for commit {commit_hash} did not return expected results structure: {test_results}"
            )
