import React from "react";
import ComplaintForm from "./components/ComplaintForm";
import AICopilotPanel from "./components/AICopilotPanel";
import ComplaintList from "./components/ComplaintList";

export default function App() {
  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">
          <div className="brand-mark">AV</div>
          <div>
            <div className="brand-name">AIVOA · Customer Complaint Management</div>
            <div className="brand-sub">Pharmaceutical API / FDF Quality Management System</div>
          </div>
        </div>
        <span className="pill pill-neutral">AI Agent: Online</span>
      </div>

      <div className="main-layout">
        <div className="layout-left">
          <ComplaintForm />
          <ComplaintList />
        </div>
        <div className="layout-right">
          <AICopilotPanel />
        </div>
      </div>
    </div>
  );
}
