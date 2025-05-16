# Software Factory Diagrams

This directory contains Mermaid diagrams that visualize the architecture, components, processes, and relationships within the Software Factory system - an autonomous AI software development team.

## Diagram Overview

### System Architecture

- **[system_architecture.mmd](system_architecture.mmd)**: High-level overview of the entire system, showing major components and their relationships.

### Agent Structure & Communication

- **[agent_hierarchy.mmd](agent_hierarchy.mmd)**: The hierarchical structure of the AI agents and their reporting relationships.
- **[agent_framework.mmd](agent_framework.mmd)**: Class diagram of the agent framework showing inheritance and capabilities.
- **[communication_protocol.mmd](communication_protocol.mmd)**: Structure of the agent-to-agent communication protocol.
- **[agent_communication.mmd](agent_communication.mmd)**: Sequence diagram showing typical communication flow between agents.
- **[agent_thinking_process.mmd](agent_thinking_process.mmd)**: Flow diagram of an agent's cognitive process from input to action.

### Database & Storage

- **[database_schema.mmd](database_schema.mmd)**: Core database tables and relationships.
- **[artifact_repository_schema.mmd](artifact_repository_schema.mmd)**: Schema for the artifact repository storage system.

### Processes & Workflows

- **[development_lifecycle.mmd](development_lifecycle.mmd)**: The end-to-end software development process.
- **[implementation_iterations.mmd](implementation_iterations.mmd)**: Gantt chart of the implementation iterations.
- **[user_journey.mmd](user_journey.mmd)**: Journey diagram showing the user experience with the system.

### Deployment

- **[deployment_architecture.mmd](deployment_architecture.mmd)**: Architecture diagram showing the deployment on Google Cloud Platform.

## Using These Diagrams

These diagrams are created using [Mermaid](https://mermaid.js.org/), a JavaScript-based diagramming and charting tool that renders Markdown-inspired text definitions to create diagrams.

### Viewing the Diagrams

1. **GitHub Rendering**: GitHub natively renders Mermaid diagrams in Markdown files. You can view them directly on GitHub by opening the .mmd files.

2. **Mermaid Live Editor**: You can copy the content of any .mmd file and paste it into the [Mermaid Live Editor](https://mermaid.live/) to view, edit, and export the diagrams.

3. **Visual Studio Code**: If you're using VS Code, you can install the "Mermaid Preview" extension to render the diagrams directly in your editor.

4. **Command Line**: You can use the Mermaid CLI to generate SVG or PNG files from the .mmd files:
   ```bash
   npx @mermaid-js/mermaid-cli -i input.mmd -o output.svg
   ```

### Modifying the Diagrams

To modify these diagrams:

1. Edit the .mmd files directly using any text editor.
2. Follow the [Mermaid syntax](https://mermaid.js.org/syntax/flowchart.html) for the specific diagram type.
3. Test your changes using one of the viewing methods above.

## Diagram Types Used

- **Flowchart**: Used for system architecture, agent hierarchy, and process flows.
- **Sequence Diagram**: Used for agent communication flows.
- **Class Diagram**: Used for object relationships in the agent framework.
- **Entity Relationship Diagram**: Used for database schema representation.
- **Gantt Chart**: Used for implementation timeline.
- **Journey Diagram**: Used for user experience mapping.
- **Architecture Diagram**: Used for deployment architecture.

## Relationship to Blueprint

These diagrams provide visual representations of the concepts described in the [blueprint.md](../blueprint.md) document and the implementation plans in the [phases](../phases/) directory. They are designed to help understand the complex components and interactions within the Software Factory system.
