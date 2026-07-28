"""
LangGraph StateGraph wiring the complaint-processing pipeline.
"""
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from app.agents.nodes import (
    extract_fields_node,
    completeness_check_node,
    risk_classification_node,
    root_cause_node,
    capa_recommendation_node,
    duplicate_detection_node,
    summary_node,
)


class ComplaintState(TypedDict, total=False):
    raw_text: str
    recent_complaints: List[dict]
    extracted_fields: dict
    completeness: dict
    risk: dict
    root_cause: dict
    capa: dict
    duplicate: dict
    summary: str
    trace: List[dict]


def build_graph():
    graph = StateGraph(ComplaintState)

    graph.add_node("extract_fields_stage", extract_fields_node)
    graph.add_node("completeness_check_stage", completeness_check_node)
    graph.add_node("risk_classification_stage", risk_classification_node)
    graph.add_node("root_cause_analysis_stage", root_cause_node)
    graph.add_node("capa_recommendation_stage", capa_recommendation_node)
    graph.add_node("duplicate_detection_stage", duplicate_detection_node)
    graph.add_node("summary_generation_stage", summary_node)

    graph.set_entry_point("extract_fields_stage")
    graph.add_edge("extract_fields_stage", "completeness_check_stage")
    graph.add_edge("completeness_check_stage", "risk_classification_stage")
    graph.add_edge("risk_classification_stage", "root_cause_analysis_stage")
    graph.add_edge("root_cause_analysis_stage", "capa_recommendation_stage")
    graph.add_edge("capa_recommendation_stage", "duplicate_detection_stage")
    graph.add_edge("duplicate_detection_stage", "summary_generation_stage")
    graph.add_edge("summary_generation_stage", END)

    return graph.compile()


complaint_graph = build_graph()


def run_complaint_pipeline(raw_text: str, recent_complaints: Optional[List[dict]] = None) -> ComplaintState:
    initial_state: ComplaintState = {
        "raw_text": raw_text,
        "recent_complaints": recent_complaints or [],
        "trace": [],
    }
    return complaint_graph.invoke(initial_state)
