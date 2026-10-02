from typing import Union, List
from langgraph.graph import StateGraph, END, START
from agents.state import MatchingState
from agents.nodes import (
    retrieval_node, 
    inclusion_node, 
    exclusion_node,
    auditor_node, 
    synthesis_node
)

def route_after_retrieval(state: MatchingState) -> Union[str, List[str]]:
    """
    Early-exit / Fast-path router.
    Routes directly to synthesis on fast-path detection, cache hits, or retrieval errors.
    Otherwise, triggers parallel evaluation across inclusion and exclusion agents concurrently.
    """
    if state.get("error"):
        return "synthesis"
    
    return ["inclusion_check", "exclusion_check"]

def should_continue(state: MatchingState) -> Union[str, List[str]]:
    """
    Conditional router for Reflexion and self-correction.
    Proceeds directly to synthesis upon an audit pass or when reaching maximum retry attempts (2).
    Otherwise, triggers simultaneous re-evaluation across both eligibility branches.
    """
    audit_passed = state.get("audit_passed", False)
    loop_count = state.get("audit_loop_count", 0)

    if audit_passed or loop_count >= 2:
        return "synthesis"
    
    return ["inclusion_check", "exclusion_check"]

def build_clinical_matching_graph():
    """
    Compiles the multi-agent graph with parallel execution, reflexion loops,
    and dynamic routing.
    """
    workflow = StateGraph(MatchingState)
    
    # 1. Register Core Agent Nodes
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("inclusion_check", inclusion_node)
    workflow.add_node("exclusion_check", exclusion_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("synthesis", synthesis_node)
    
    # 2. Pipeline Entry Point
    workflow.add_edge(START, "retrieval")
    
    # 3. Dynamic Conditional Route After Retrieval (Direct Fast-Path or Parallel Evaluation)
    workflow.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {
            "synthesis": "synthesis",
            "inclusion_check": "inclusion_check",
            "exclusion_check": "exclusion_check"
        }
    )
    
    # 4. Fan-in: Inclusion and Exclusion Agents converge simultaneously at the Auditor
    workflow.add_edge("inclusion_check", "auditor")
    workflow.add_edge("exclusion_check", "auditor")
    
    # 5. Reflexion Self-Correction Dynamic Routing
    workflow.add_conditional_edges(
        "auditor",
        should_continue,
        {
            "synthesis": "synthesis",
            "inclusion_check": "inclusion_check",
            "exclusion_check": "exclusion_check"
        }
    )
    
    # 6. Pipeline Exit
    workflow.add_edge("synthesis", END)
    
    return workflow.compile()