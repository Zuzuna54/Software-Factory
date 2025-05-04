import React from 'react';

interface AgentDetailPageProps {
    params: {
        agentId: string;
    };
}

export default function AgentDetailPage({ params }: AgentDetailPageProps) {
    const { agentId } = params;

    return (
        <div>
            <h1>Agent Detail: {agentId}</h1>
            <p>Details for agent {agentId} will be displayed here.</p>
            {/* TODO: Fetch and display agent details, activity, messages */}
        </div>
    );
} 