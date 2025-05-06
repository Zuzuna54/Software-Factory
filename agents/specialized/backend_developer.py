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

    DEFAULT_CAPABILITIES = {
        "can_write_code": True,
        "can_refactor_code": True,
        "can_fix_bugs": True,
        "can_write_api_endpoints": True,
        "can_work_with_db": True,
    }

    def __init__(self, git_client: Optional[GitClient] = None, **kwargs):
        """Initialize the Backend Developer Agent."""
        capabilities = self.DEFAULT_CAPABILITIES.copy()
        if "capabilities" in kwargs:
            capabilities.update(kwargs["capabilities"])
        kwargs["capabilities"] = capabilities

        # Let BaseAgent handle initialization via kwargs, including agent_type
        super().__init__(**kwargs)

        self.logger.info(
            f"BackendDeveloperAgent {self.agent_id} ({self.agent_name}) initialized."
        )
        self.git_client = git_client

    async def implement_api_endpoint(
        self,
        endpoint_name: str,
        endpoint_description: str,
        http_method: str = "GET",
        request_parameters: Optional[Dict[str, Any]] = None,
        response_structure: Optional[Dict[str, Any]] = None,
        related_task_id: Optional[str] = None,
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
                "response_structure": response_structure,
            },
        )

        # Use the LLM to generate the implementation
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during API implementation: {error}")
            return {"error": error}

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find("{")
            end_idx = thought.rfind("}") + 1

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
                    author_email="backend@ai-agents.com",
                )

            # Log the successful implementation
            await self.log_activity(
                activity_type="APIImplementationComplete",
                description=f"Successfully implemented {http_method} endpoint {endpoint_name}",
                related_task_id=related_task_id,
                related_files=list(created_files),
                output_data={
                    "files_created": created_files,
                    "commit_hash": commit_hash,
                },
            )

            return {
                "success": True,
                "files_created": created_files,
                "commit_hash": commit_hash,
            }

        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error parsing implementation: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="APIImplementationError",
                description="Failed to parse implementation result",
                related_task_id=related_task_id,
                output_data={"error": str(e), "raw_result": thought[:500]},
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
        context = "Existing codebase patterns:\\n\\n"

        for result in results:
            context += f"File: {result['title']}\\n"
            context += f"Content sample: {result['content'][:200]}...\\n\\n"

        return context

    async def _write_implementation_files(
        self, implementation: Dict[str, str]
    ) -> Dict[str, str]:
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
            with open(file_path, "w") as f:
                f.write(content)

            created_files[file_path] = content
            self.logger.info(f"Created file: {file_path}")

        return created_files

    async def fix_code_issue(
        self,
        file_path: str,
        issue_description: str,
        test_failure: Optional[str] = None,
        related_task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fix an issue in the code based on a description and/or test failure.
        """
        # Read the current file content
        if not os.path.exists(file_path):
            error_msg = f"File {file_path} does not exist"
            self.logger.error(error_msg)
            return {"error": error_msg}

        with open(file_path, "r") as f:
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
                "test_failure": test_failure,
            },
        )

        # Use the LLM to generate the fix
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during code fix: {error}")
            return {"error": error}

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find("{")
            end_idx = thought.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in the response")

            json_str = thought[start_idx:end_idx]
            fix_result = json.loads(json_str)

            # Write the fixed file
            with open(file_path, "w") as f:
                f.write(fix_result["fixed_code"])

            # Commit the changes if git client is available
            commit_hash = None
            if self.git_client:
                commit_msg = f"fix: {issue_description.split('.')[0]}"
                commit_hash = await self.git_client.commit_changes(
                    [file_path],
                    commit_msg,
                    author_name="Backend Developer Agent",
                    author_email="backend@ai-agents.com",
                )

            # Log the successful fix
            await self.log_activity(
                activity_type="CodeFixComplete",
                description=f"Successfully fixed issue in {file_path}",
                related_task_id=related_task_id,
                related_files=[file_path],
                output_data={
                    "explanation": fix_result.get("explanation", ""),
                    "commit_hash": commit_hash,
                },
            )

            return {
                "success": True,
                "file_path": file_path,
                "explanation": fix_result.get("explanation", ""),
                "commit_hash": commit_hash,
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
                output_data={"error": str(e), "raw_result": thought[:500]},
            )

            return {"error": error_msg, "raw_response": thought[:500]}
