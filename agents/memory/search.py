# agents/memory/search.py

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import uuid

from ..db.postgres import PostgresClient
from ..llm.base import LLMProvider
from .vector_memory import EnhancedVectorMemory  # Updated import


class MemorySearch:
    """Memory search utilities for finding relevant information in the knowledge base."""

    def __init__(
        self,
        db_client: PostgresClient,
        vector_memory: EnhancedVectorMemory,  # Updated type hint
        llm_provider: LLMProvider,
    ):
        self.db_client = db_client
        self.vector_memory = vector_memory
        self.llm_provider = llm_provider
        self.logger = logging.getLogger("agent.memory.search")

    async def search_memory(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        threshold: float = 0.7,  # Added threshold parameter
        expand_relationships: bool = False,
        include_content: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search the memory for information related to the query.

        Args:
            query: Natural language query to search for
            entity_types: Optional list of entity types to search within
            tags: Optional list of tags to filter by
            metadata_filter: Optional metadata conditions to filter by
            limit: Maximum number of direct results to return
            threshold: Minimum similarity score for direct results
            expand_relationships: Whether to include related entities
            include_content: Whether to include the full content in results

        Returns:
            List of matching items from memory
        """
        if not self.llm_provider or not self.vector_memory:
            self.logger.error("LLM provider or vector memory not available for search")
            return []

        # Generate embedding for the query
        try:
            query_embedding = await self.llm_provider.generate_embeddings(query)
            if not query_embedding:
                self.logger.warning(
                    f"Failed to generate embedding for query: {query[:100]}..."
                )
                return []
        except Exception as e:
            self.logger.error(
                f"Error generating embedding for query '{query[:50]}...': {e}",
                exc_info=True,
            )
            return []

        # Search for similar entities using EnhancedVectorMemory
        similar_entities = await self.vector_memory.search_similar(
            query_embedding=query_embedding,
            entity_types=entity_types,
            tags=tags,
            metadata_filter=metadata_filter,
            limit=limit,
            threshold=threshold,  # Pass threshold to search_similar
        )

        results = []
        processed_entity_keys = set()  # Track entities added to results (type:id)

        # Process direct results
        for entity in similar_entities:
            entity_key = f"{entity['entity_type']}:{entity['entity_id']}"
            if entity_key in processed_entity_keys:
                continue  # Avoid duplicates if relationships bring back same entity

            result = {
                "id": entity["id"],  # Use internal UUID if available
                "entity_type": entity["entity_type"],
                "entity_id": entity["entity_id"],
                "similarity": entity["similarity"],
                "metadata": entity["metadata"],
                "tags": entity["tags"],
                "created_at": entity["created_at"],
                "updated_at": entity["updated_at"],
                "match_type": "direct",
            }

            if include_content:
                result["content"] = entity["content"]

            results.append(result)
            processed_entity_keys.add(entity_key)

        # Expand relationships if requested
        if expand_relationships:
            entities_to_expand = (
                similar_entities  # Expand relationships of direct matches
            )
            # Limit expansion depth/breadth to avoid excessive queries
            max_related_per_entity = 5
            max_total_related = limit * 2  # Limit total results roughly

            for entity in entities_to_expand:
                if len(results) >= max_total_related:
                    break

                related_items = await self.vector_memory.get_related_entities(
                    entity_type=entity["entity_type"],
                    entity_id=entity["entity_id"],
                    limit=max_related_per_entity,
                )

                for rel in related_items:
                    if len(results) >= max_total_related:
                        break

                    related_entity = rel["related_entity"]
                    related_key = (
                        f"{related_entity['entity_type']}:{related_entity['entity_id']}"
                    )

                    # Skip if we've already included this entity
                    if related_key in processed_entity_keys:
                        continue

                    processed_entity_keys.add(related_key)

                    result = {
                        "id": related_entity["internal_id"],  # Use internal UUID
                        "entity_type": related_entity["entity_type"],
                        "entity_id": related_entity["entity_id"],
                        "similarity": None,  # No direct similarity score for related items
                        "metadata": related_entity["metadata"],
                        "tags": related_entity["tags"],
                        "created_at": related_entity["created_at"],
                        "updated_at": related_entity["updated_at"],
                        "match_type": "related",
                        "relationship": {
                            "id": rel["relationship_id"],
                            "type": rel["relationship_type"],
                            "direction": rel["direction"],
                            # Determine source/target based on direction
                            "source": (
                                entity_key
                                if rel["direction"] == "outgoing"
                                else related_key
                            ),
                            "target": (
                                related_key
                                if rel["direction"] == "outgoing"
                                else entity_key
                            ),
                            "metadata": rel["relationship_metadata"],
                        },
                    }

                    if include_content:
                        result["content"] = related_entity["content"]

                    results.append(result)

        self.logger.debug(
            f"Memory search returned {len(results)} results for query: {query[:50]}..."
        )
        return results

    async def analyze_results(
        self, query: str, search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze search results to extract key insights and relevance.

        Args:
            query: The original search query
            search_results: Results from search_memory

        Returns:
            Analysis of the search results
        """
        if not self.llm_provider:
            return {"error": "LLM provider not available for analysis."}
        if not search_results:
            return {"relevant_count": 0, "summary": "No results to analyze."}

        system_message = """You are analyzing search results to determine their relevance to a query.
        Examine each result and provide:
        1. How many results seem truly relevant to the query based on content/metadata.
        2. A brief summary of the key information found across the relevant results.
        3. Any important connections or patterns observed (e.g., related items).
        4. Suggestions for refining the search if needed (e.g., different keywords, filters).

        Be concise and focus on the most important information. Base relevance on content/meaning, not just the similarity score.
        Respond in JSON format with keys: relevant_count, summary, patterns, suggestions.
        """

        # Prepare results for analysis
        result_summary = []
        for i, res in enumerate(search_results[:15]):  # Limit context for LLM
            content_preview = res.get("content", "")
            if content_preview and len(content_preview) > 250:
                content_preview = content_preview[:250] + "..."

            relation_info = ""
            if res.get("match_type") == "related":
                rel = res.get("relationship", {})
                relation_info = (
                    f" (Related via {rel.get('type')} {rel.get('direction')})"
                )

            result_summary.append(
                f"\nResult {i+1}:{relation_info}\n"
                f"- Type: {res['entity_type']}:{res['entity_id']}\n"
                f"- Similarity: {res.get('similarity', 'N/A'):.2f}\n"
                f"- Tags: {res.get('tags', [])}\n"
                f"- Preview: {content_preview}"
            )

        prompt = f"""
        Query: "{query}"

        Search Results Overview:
        {''.join(result_summary)}

        Analyze these results for relevance and key insights based on the query. Provide your analysis in JSON format as requested.
        """

        try:
            analysis_text, error = await self.llm_provider.generate_completion(
                prompt=prompt,
                system_message=system_message,
                temperature=0.2,  # Lower temp for focused analysis
            )

            if error:
                self.logger.error(f"Error analyzing results via LLM: {error}")
                return {"error": error}

            # Attempt to parse the JSON response from LLM
            try:
                # Find JSON object boundaries
                start_idx = analysis_text.find("{")
                end_idx = analysis_text.rfind("}") + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = analysis_text[start_idx:end_idx]
                    analysis_json = json.loads(json_str)
                    # Add original query and counts for context
                    analysis_json["query"] = query
                    analysis_json["total_results_provided"] = len(search_results)
                    return analysis_json
                else:
                    # Fallback if no JSON found, return raw text
                    self.logger.warning(
                        f"LLM analysis response was not valid JSON: {analysis_text}"
                    )
                    return {
                        "analysis_raw": analysis_text,
                        "query": query,
                        "total_results_provided": len(search_results),
                    }
            except json.JSONDecodeError as json_e:
                self.logger.error(
                    f"Failed to parse LLM analysis JSON: {json_e}\nRaw text: {analysis_text}"
                )
                return {
                    "error": "Failed to parse analysis JSON",
                    "analysis_raw": analysis_text,
                }

        except Exception as e:
            self.logger.error(f"Error during result analysis: {e}", exc_info=True)
            return {"error": str(e)}
