This file contains the articulate_vision_logic function, responsible for generating and storing a project vision.
Function Signature:
async def articulate_vision_logic(agent: Any, project_id: uuid.UUID, project_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
Purpose:
To create a comprehensive project vision based on a project description and any additional context. This vision includes a statement, target audience, key goals, success metrics, constraints, and a unique value proposition.
Execution Flow & Decision Tree:
Initialization:
operation_name is set to "articulate_vision".
A timer is started using agent.activity_logger.start_timer().
execution_time_s is initialized to 0.
Logging - Start:
Logs an activity "vision_articulation_started" with details like project_id, description_length, and context.
Prompt Engineering:
A detailed prompt is constructed for the LLM.
This prompt instructs the LLM to create a vision statement based on the project_description and optional context.
Crucially, it specifies that the LLM's response MUST BE ONLY a single, valid JSON object conforming to a defined schema. The schema includes fields:
vision_statement (string)
target_audience (string)
key_goals (list of strings)
success_metrics (dictionary of metric_name: description)
constraints (list of strings)
unique_value_proposition (string)
LLM Interaction:
agent.llm_provider.generate_text(prompt) is called to get the generated_text and llm_metadata from the language model.
Logs the raw generated_text from the LLM for debugging ("debug\llm_generated_text_vision").
JSON Parsing (Decision Point):
Try: Attempts to parse generated_text using json.loads().
If Successful: The parsed JSON is stored in the vision dictionary.
If json.JSONDecodeError Occurs (Exception):
An error "VisionArticulationJSONDecodeError" is logged, including the raw_response and error message.
The vision dictionary remains empty or in its previous state (which is empty if this is the first attempt). Note: The code doesn't explicitly set vision to a default error structure here, but proceeds. The impact is that vision.get(...) calls later will return defaults.
Logging - Parsed Content:
Logs the (potentially parsed or empty) vision content before saving ("debug\vision_content_before_save"), including the vision_statement or a default message if not found.
Database Interaction (Decision Point):
If agent.db_session exists (meaning a database session is available):
A ProjectVision ORM object is instantiated.
title is set to f"Project Vision for {project_id}".
description is set to vision.get("vision_statement", "No explicit description provided in vision object."). This indicates a potential area for clarification: the prompt asks for vision_statement, and the database model ProjectVision has both description and vision_statement fields. Here, vision_statement is used as a fallback for description.
Other fields of ProjectVision (project_id, created_by, vision_statement, target_audience, key_goals, success_metrics, constraints) are populated using vision.get() with appropriate defaults (e.g., empty lists or dicts for JSONB fields if the key is missing from the LLM's JSON output).
status is set to "articulated".
The project_vision_data object is added to the session: agent.db_session.add(project_vision_data).
The session is committed: await agent.db_session.commit().
Logging & Timer - Success:
The timer for the operation is stopped with success=True.
An activity "vision\articulation_completed" is logged with details like project_id, vision_statement_length, and execution_time_ms.
The (parsed or empty) vision dictionary is returned.
Exception Handling (Outer try...except):
If any Exception occurs during the process (e.g., LLM error, database error not caught by inner try-except):
If agent.db_session exists: await agent.db_session.rollback() is called to revert any pending database changes.
The timer is stopped with success=False.
An error "VisionArticulationError" is logged with the exception details, severity, and context.
The exception is re-raised (raise).
Key Decisions/Logic Branches:
Presence of context: The prompt to the LLM changes slightly if context is provided.
LLM response validity (JSON parsing): If the LLM does not return valid JSON, error logging occurs, but the function attempts to proceed, relying on vision.get() defaults.
Database availability (agent.db_session): Vision data is only saved to the DB if a session is available.
General success/failure of the entire operation: Dictates logging, timer status, and whether an exception is ultimately raised.
Outputs:
Returns a dictionary (vision) which ideally contains the structured project vision parsed from the LLM. If parsing fails or the LLM provides unexpected output, this dictionary might be partially filled or empty, relying on the get method's defaults when accessed by the caller or during DB insertion.
Side effects: Creates a ProjectVision record in the database if successful and DB session is available. Logs various activities and errors.
