# Iteration 3: "Hello World" Development & QA Loop

## Overview

This phase implements the first functional development loop by creating the Backend Developer and QA agents. We'll establish the version control integration, continuous integration pipeline, and the feedback mechanism between developers and testers. This creates the foundation for autonomous code generation, testing, and improvement.

## Why This Phase Matters

The development and QA loop represents the core value creation process of our system. By implementing this loop, we enable the autonomous creation, testing, and refinement of code. This establishes the pattern for how all future features will be developed.

## Expected Outcomes

After completing this phase, we will have:

1. A `BackendDeveloperAgent` capable of generating Python code
2. A `QAAgent` for testing and validating code changes
3. Git integration for committing code and managing branches
4. Continuous integration hooks for automated testing
5. A feedback loop between QA and Developer agents
6. The ability to autonomously implement, test, and fix a simple API endpoint

## Implementation Tasks

### Task 1: Backend Developer Agent Implementation

**What needs to be done:**
Create a Backend Developer agent capable of generating Python code based on tasks and requirements.

**Why this task is necessary:**
The Backend Developer agent is responsible for translating requirements into executable code, which is the primary output of our system.

**Files to be created:**

- `agents/specialized/backend_developer.py` - Backend Developer agent implementation

**Implementation guidelines:**

````python
# agents/specialized/backend_developer.py

import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..base_agent import BaseAgent
from ..git.git_client import GitClient

class BackendDeveloperAgent(BaseAgent):
    """
    Backend Developer Agent - Responsible for implementing server-side
    functionality based on requirements and tasks.
    """

    def __init__(self, git_client: Optional[GitClient] = None, **kwargs):
        super().__init__(
            agent_type="backend_developer",
            agent_name="Backend Developer",
            capabilities={
                "python_coding": True,
                "api_development": True,
                "database_integration": True,
                "code_review": True,
                "testing": True
            },
            **kwargs
        )
        self.logger = logging.getLogger(f"agent.backend.{self.agent_id}")
        self.git_client = git_client

    async def implement_api_endpoint(
        self,
        endpoint_name: str,
        endpoint_description: str,
        http_method: str = "GET",
        request_parameters: Optional[Dict[str, Any]] = None,
        response_structure: Optional[Dict[str, Any]] = None,
        related_task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Implement a new API endpoint based on the specifications.
        """
        # First, analyze the existing codebase to understand patterns and structure
        codebase_context = await self._analyze_codebase()

        system_message = """You are a Python backend developer implementing a FastAPI endpoint.
        You need to create a well-structured, tested endpoint that follows the project's coding style.
        Your code should:
        1. Be compatible with Python 3.12 and FastAPI
        2. Include appropriate documentation, type hints, and error handling
        3. Follow best practices for API design
        4. Include test cases for the endpoint

        Generate the complete implementation, including:
        1. Route definition with appropriate HTTP method and path
        2. Request and response models if needed
        3. Request validation
        4. Handler function with business logic
        5. API documentation for endpoint using FastAPI docstrings
        6. Error handling for expected failure cases
        7. Test file with pytest cases for the endpoint"""

        # Construct a detailed prompt with all the context
        prompt = f"""
        I need to implement a new API endpoint with the following specifications:

        Endpoint Name: {endpoint_name}
        HTTP Method: {http_method}
        Description: {endpoint_description}

        Request Parameters: {json.dumps(request_parameters or {}, indent=2)}
        Response Structure: {json.dumps(response_structure or {}, indent=2)}

        Existing Codebase Context:
        {codebase_context}

        Please provide a complete implementation including:
        1. The endpoint implementation file
        2. A test file for the endpoint

        Format your response as JSON with separate fields for each file to be created,
        using the file path as the key and the file content as the value.
        """

        # Log that we're starting implementation
        await self.log_activity(
            activity_type="APIImplementation",
            description=f"Implementing {http_method} endpoint {endpoint_name}",
            related_task_id=related_task_id,
            input_data={
                "endpoint_name": endpoint_name,
                "http_method": http_method,
                "description": endpoint_description,
                "request_parameters": request_parameters,
                "response_structure": response_structure
            }
        )

        # Use the LLM to generate the implementation
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during API implementation: {error}")
            return {"error": error}

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find('{')
            end_idx = thought.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in the response")

            json_str = thought[start_idx:end_idx]
            implementation = json.loads(json_str)

            # Write the files to disk
            created_files = await self._write_implementation_files(implementation)

            # Commit the changes if git client is available
            commit_hash = None
            if self.git_client:
                commit_msg = f"feat: Implement {http_method} {endpoint_name} endpoint"
                commit_hash = await self.git_client.commit_changes(
                    created_files,
                    commit_msg,
                    author_name="Backend Developer Agent",
                    author_email="backend@ai-agents.com"
                )

            # Log the successful implementation
            await self.log_activity(
                activity_type="APIImplementationComplete",
                description=f"Successfully implemented {http_method} endpoint {endpoint_name}",
                related_task_id=related_task_id,
                related_files=list(created_files),
                output_data={
                    "files_created": created_files,
                    "commit_hash": commit_hash
                }
            )

            return {
                "success": True,
                "files_created": created_files,
                "commit_hash": commit_hash
            }

        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error parsing implementation: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="APIImplementationError",
                description="Failed to parse implementation result",
                related_task_id=related_task_id,
                output_data={"error": str(e), "raw_result": thought[:500]}
            )

            return {"error": error_msg, "raw_response": thought[:500]}

    async def _analyze_codebase(self) -> str:
        """
        Analyze the existing codebase to understand patterns and structure.
        Returns a string with relevant context about the codebase.
        """
        # In a real implementation, this would use the vector memory to retrieve
        # similar code files and patterns from the existing codebase
        # For now, we'll return a simple description

        if not self.db_client or not self.vector_memory:
            return "No existing codebase context available."

        # Check if we have any Python files in the artifacts table
        query = """
        SELECT artifact_id, title, content
        FROM artifacts
        WHERE artifact_type = 'Code' AND metadata->>'language' = 'python'
        LIMIT 10
        """

        results = await self.db_client.fetch_all(query)

        if not results:
            return """
            This appears to be a new project using FastAPI.
            Follow standard FastAPI patterns with:
            - Routes in app/api/endpoints/ directory
            - Pydantic models in app/models/ directory
            - Business logic in app/services/ directory
            - Tests in tests/ directory
            """

        # Analyze the files to extract patterns
        context = "Existing codebase patterns:\n\n"

        for result in results:
            context += f"File: {result['title']}\n"
            context += f"Content sample: {result['content'][:200]}...\n\n"

        return context

    async def _write_implementation_files(self, implementation: Dict[str, str]) -> Dict[str, str]:
        """
        Write the implementation files to disk.
        Returns a dictionary of file paths and their content.
        """
        created_files = {}

        for file_path, content in implementation.items():
            # Make sure the directory exists
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)

            # Write the file
            with open(file_path, 'w') as f:
                f.write(content)

            created_files[file_path] = content
            self.logger.info(f"Created file: {file_path}")

        return created_files

    async def fix_code_issue(
        self,
        file_path: str,
        issue_description: str,
        test_failure: Optional[str] = None,
        related_task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fix an issue in the code based on a description and/or test failure.
        """
        # Read the current file content
        if not os.path.exists(file_path):
            error_msg = f"File {file_path} does not exist"
            self.logger.error(error_msg)
            return {"error": error_msg}

        with open(file_path, 'r') as f:
            current_content = f.read()

        system_message = """You are a Python backend developer fixing an issue in the code.
        You will be provided with the current code and a description of the issue or test failure.
        Carefully analyze the issue and provide a fixed version of the code that resolves the problem.
        Explain the changes you've made in a clear, concise manner."""

        prompt = f"""
        I need to fix an issue in the following code:

        File: {file_path}

        ```python
        {current_content}
        ```

        Issue Description: {issue_description}

        {"Test Failure: " + test_failure if test_failure else ""}

        Please provide the fixed version of the file as JSON with:
        1. "fixed_code": The complete fixed code
        2. "explanation": A brief explanation of the changes made
        """

        # Log that we're starting the fix
        await self.log_activity(
            activity_type="CodeFix",
            description=f"Fixing issue in {file_path}",
            related_task_id=related_task_id,
            related_files=[file_path],
            input_data={
                "file_path": file_path,
                "issue_description": issue_description,
                "test_failure": test_failure
            }
        )

        # Use the LLM to generate the fix
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during code fix: {error}")
            return {"error": error}

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find('{')
            end_idx = thought.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in the response")

            json_str = thought[start_idx:end_idx]
            fix_result = json.loads(json_str)

            # Write the fixed file
            with open(file_path, 'w') as f:
                f.write(fix_result["fixed_code"])

            # Commit the changes if git client is available
            commit_hash = None
            if self.git_client:
                commit_msg = f"fix: {issue_description.split('.')[0]}"
                commit_hash = await self.git_client.commit_changes(
                    [file_path],
                    commit_msg,
                    author_name="Backend Developer Agent",
                    author_email="backend@ai-agents.com"
                )

            # Log the successful fix
            await self.log_activity(
                activity_type="CodeFixComplete",
                description=f"Successfully fixed issue in {file_path}",
                related_task_id=related_task_id,
                related_files=[file_path],
                output_data={
                    "explanation": fix_result.get("explanation", ""),
                    "commit_hash": commit_hash
                }
            )

            return {
                "success": True,
                "file_path": file_path,
                "explanation": fix_result.get("explanation", ""),
                "commit_hash": commit_hash
            }

        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error parsing fix result: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="CodeFixError",
                description="Failed to parse fix result",
                related_task_id=related_task_id,
                related_files=[file_path],
                output_data={"error": str(e), "raw_result": thought[:500]}
            )

            return {"error": error_msg, "raw_response": thought[:500]}
````

### Task 2: QA Agent Implementation

**What needs to be done:**
Create a QA agent capable of testing and validating code changes.

**Why this task is necessary:**
Automated testing is essential for ensuring code quality and catching bugs before they reach production.

**Files to be created:**

- `agents/specialized/qa_agent.py` - QA agent implementation

**Implementation guidelines:**

````python
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

class QAAgent(BaseAgent):
    """
    QA Agent - Responsible for testing and validating code changes.
    """

    def __init__(self, **kwargs):
        super().__init__(
            agent_type="qa",
            agent_name="QA Agent",
            capabilities={
                "code_testing": True,
                "test_automation": True,
                "bug_reporting": True,
                "code_quality": True,
                "regression_testing": True
            },
            **kwargs
        )
        self.logger = logging.getLogger(f"agent.qa.{self.agent_id}")

    async def run_tests(
        self,
        test_paths: Optional[List[str]] = None,
        related_task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run tests and report results.
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
            input_data={"test_paths": test_paths}
        )

        # Run pytest in a subprocess
        cmd = ["pytest", "-v"]
        cmd.extend(test_paths)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

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
                    "failing_tests": test_results["failing_tests"]
                }
            )

            # If tests failed, analyze the failures
            if return_code != 0 and test_results["failing_tests"]:
                analysis = await self._analyze_test_failures(test_results["failing_tests"])

                # Log the analysis
                await self.log_activity(
                    activity_type="TestFailureAnalysis",
                    description=f"Analyzed {len(test_results['failing_tests'])} test failures",
                    related_task_id=related_task_id,
                    output_data={"analysis": analysis}
                )

                # Return results with analysis
                return {
                    "success": False,
                    "return_code": return_code,
                    "summary": test_results["summary"],
                    "failing_tests": test_results["failing_tests"],
                    "analysis": analysis
                }

            # Return results
            return {
                "success": return_code == 0,
                "return_code": return_code,
                "summary": test_results["summary"],
                "failing_tests": test_results["failing_tests"]
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
                output_data={"error": str(e)}
            )

            return {"error": error_msg}

    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """
        Parse pytest output to extract test results.
        """
        # Extract summary line (e.g., "2 failed, 3 passed in 0.12s")
        summary_match = re.search(r'=+ (.+) in \d+\.\d+s =+', output)
        summary = summary_match.group(1) if summary_match else "Unknown result"

        # Extract failing tests
        failing_tests = []

        # Look for lines like "FAILED tests/test_api.py::test_create_item"
        failed_lines = re.finditer(r'FAILED (.+?)::(.+?)(\[.+\])?\s', output)
        for match in failed_lines:
            file_path = match.group(1)
            test_name = match.group(2)

            # Find the error message for this test
            error_regex = re.escape(f"{file_path}::{test_name}") + r'.*?\n(.*?)(?:=|Captured|\Z)'
            error_match = re.search(error_regex, output, re.DOTALL)
            error_msg = error_match.group(1).strip() if error_match else "Unknown error"

            failing_tests.append({
                "file_path": file_path,
                "test_name": test_name,
                "error_message": error_msg
            })

        return {
            "summary": summary,
            "failing_tests": failing_tests
        }

    async def _analyze_test_failures(self, failing_tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze test failures to determine the root cause and possible solutions.
        """
        if not self.llm_provider:
            self.logger.warning("No LLM provider available, skipping test failure analysis")
            return []

        analyzed_failures = []

        for test in failing_tests:
            file_path = test["file_path"]
            test_name = test["test_name"]
            error_message = test["error_message"]

            # Read the test file
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    test_content = f.read()
            else:
                test_content = "File not found"

            # Find the implementation file being tested
            impl_file_path = self._guess_implementation_file(file_path)
            impl_content = "File not found"

            if impl_file_path and os.path.exists(impl_file_path):
                with open(impl_file_path, 'r') as f:
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
                    "analysis_error": error
                }
            else:
                try:
                    # Extract JSON from the response
                    start_idx = thought.find('{')
                    end_idx = thought.rfind('}') + 1

                    if start_idx == -1 or end_idx == 0:
                        raise ValueError("No JSON object found in the response")

                    json_str = thought[start_idx:end_idx]
                    analysis_result = json.loads(json_str)

                    analysis = {
                        "file_path": file_path,
                        "test_name": test_name,
                        "error_message": error_message,
                        "root_cause": analysis_result.get("root_cause", "Unknown"),
                        "file_to_modify": analysis_result.get("file_to_modify", "Unknown"),
                        "suggested_solution": analysis_result.get("suggested_solution", "Unknown")
                    }

                except (json.JSONDecodeError, ValueError) as e:
                    analysis = {
                        "file_path": file_path,
                        "test_name": test_name,
                        "error_message": error_message,
                        "parsing_error": str(e),
                        "raw_analysis": thought[:500]
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
        if test_file_path.startswith('tests/'):
            file_path = test_file_path[6:]  # Remove 'tests/'
        else:
            file_path = test_file_path

        # Remove 'test_' prefix from filename
        file_path = re.sub(r'test_(.+\.py)', r'\1', file_path)

        # Check common app directory structures
        possible_paths = [
            os.path.join('app', file_path),
            os.path.join('src', file_path),
            file_path
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
        related_files: Optional[List[str]] = None
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
            json.dumps({
                "steps_to_reproduce": steps_to_reproduce,
                "expected_result": expected_result,
                "actual_result": actual_result,
                "severity": severity,
                "assigned_to": assigned_to,
                "related_task_id": related_task_id,
                "related_files": related_files or []
            }),
            1
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
                "assigned_to": assigned_to
            }
        )

        # Notify the assigned developer if specified
        if assigned_to:
            await self.send_message(
                receiver_id=assigned_to,
                content=f"Bug Report: {title}\n\n{description}\n\nSeverity: {severity}",
                message_type="BUG_REPORT",
                related_task_id=related_task_id,
                metadata={"bug_id": bug_id}
            )

        return {
            "success": True,
            "bug_id": bug_id,
            "title": title,
            "assigned_to": assigned_to
        }
````

### Task 3: Git Integration

**What needs to be done:**
Implement Git integration to enable version control for code changes.

**Why this task is necessary:**
Version control is essential for tracking code changes, managing collaboration, and enabling rollback if needed.

**Files to be created:**

- `agents/git/git_client.py` - Git client implementation

**Implementation guidelines:**

```python
# agents/git/git_client.py

import asyncio
import logging
import os
import re
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union

class GitClient:
    """
    Git client for version control operations.
    """

    def __init__(self, repo_path: str = '.'):
        self.repo_path = repo_path
        self.logger = logging.getLogger("agent.git")

    async def init_repo(self) -> bool:
        """
        Initialize a new Git repository if one doesn't exist.
        """
        if os.path.exists(os.path.join(self.repo_path, '.git')):
            self.logger.info(f"Git repository already exists at {self.repo_path}")
            return True

        try:
            result = await self._run_git_command('init')
            self.logger.info(f"Initialized Git repository at {self.repo_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Git repository: {str(e)}")
            return False

    async def commit_changes(
        self,
        files: List[str],
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> Optional[str]:
        """
        Commit changes to the repository.
        Returns the commit hash if successful, None otherwise.
        """
        try:
            # Add files to staging
            for file_path in files:
                await self._run_git_command('add', file_path)

            # Set author if provided
            env = os.environ.copy()
            if author_name and author_email:
                env['GIT_AUTHOR_NAME'] = author_name
                env['GIT_AUTHOR_EMAIL'] = author_email
                env['GIT_COMMITTER_NAME'] = author_name
                env['GIT_COMMITTER_EMAIL'] = author_email

            # Commit changes
            result = await self._run_git_command('commit', '-m', message, env=env)

            # Extract commit hash
            commit_hash = await self.get_last_commit_hash()

            self.logger.info(f"Committed changes with hash {commit_hash}")
            return commit_hash

        except Exception as e:
            self.logger.error(f"Failed to commit changes: {str(e)}")
            return None

    async def create_branch(self, branch_name: str) -> bool:
        """
        Create a new branch.
        """
        try:
            await self._run_git_command('checkout', '-b', branch_name)
            self.logger.info(f"Created and switched to branch {branch_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create branch {branch_name}: {str(e)}")
            return False

    async def switch_branch(self, branch_name: str) -> bool:
        """
        Switch to an existing branch.
        """
        try:
            await self._run_git_command('checkout', branch_name)
            self.logger.info(f"Switched to branch {branch_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to switch to branch {branch_name}: {str(e)}")
            return False

    async def get_current_branch(self) -> Optional[str]:
        """
        Get the name of the current branch.
        """
        try:
            result = await self._run_git_command('branch', '--show-current')
            return result.strip()
        except Exception as e:
            self.logger.error(f"Failed to get current branch: {str(e)}")
            return None

    async def get_last_commit_hash(self) -> Optional[str]:
        """
        Get the hash of the last commit.
        """
        try:
            result = await self._run_git_command('rev-parse', 'HEAD')
            return result.strip()
        except Exception as e:
            self.logger.error(f"Failed to get last commit hash: {str(e)}")
            return None

    async def get_file_history(self, file_path: str, max_commits: int = 10) -> List[Dict[str, Any]]:
        """
        Get the commit history for a specific file.
        """
        try:
            result = await self._run_git_command(
                'log',
                f'-{max_commits}',
                '--pretty=format:%H|%an|%ae|%ad|%s',
                '--',
                file_path
            )

            commits = []
            for line in result.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'author_name': parts[1],
                        'author_email': parts[2],
                        'date': parts[3],
                        'message': parts[4]
                    })

            return commits

        except Exception as e:
            self.logger.error(f"Failed to get file history for {file_path}: {str(e)}")
            return []

    async def _run_git_command(self, *args, env=None) -> str:
        """
        Run a Git command and return the output.
        """
        cmd = ['git']
        cmd.extend(args)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.repo_path,
            env=env
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Git command failed: {stderr.decode('utf-8')}")

        return stdout.decode('utf-8')
```

## Post-Implementation Verification

After completing all tasks, verify the implementation by:

1. Testing the Backend Developer agent's ability to implement a simple "Hello World" API endpoint
2. Verifying that the QA agent can run tests and detect failures
3. Testing the bug reporting and feedback loop between Developer and QA agents
4. Checking that Git integration works correctly for committing and branching
5. Running a complete end-to-end flow from task assignment → implementation → testing → bug fixing

This phase establishes the core development loop, which will be expanded upon in subsequent iterations to include more advanced capabilities and agent roles.
