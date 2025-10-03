"""
Taipy UI Module for SPKIA
Provides advanced UI generation, scenario management, and what-if analysis for AI detection thresholds.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from taipy.gui import Gui, State, notify, invoke_callback, navigate
from taipy.core import Core, Config
from taipy.core.config import JobConfig, DataNodeConfig, ScenarioConfig
import pandas as pd
import numpy as np
from pathlib import Path
import json

from app.database import Database
from app.services.verification import VerificationService
from app.models.schemas import VerificationResult


class ThresholdScenarioManager:
    """
    Manages scenario-based threshold configurations for AI detection tuning.
    Enables what-if analysis for comparing verification outcomes across different thresholds.
    """
    
    def __init__(self, db: Database, verification_service: VerificationService):
        self.db = db
        self.verification_service = verification_service
        self.scenarios: Dict[str, Dict[str, Any]] = {}
        self._init_taipy_config()
    
    def _init_taipy_config(self):
        """Initialize Taipy Core configuration for scenario management."""
        # Data node for threshold configurations
        threshold_config = Config.configure_data_node(
            id="threshold_config",
            storage_type="json",
            scope="SCENARIO",
            default_data={
                "ensemble_threshold": 0.7,
                "cnn_weight": 0.4,
                "prnu_weight": 0.3,
                "metadata_weight": 0.3,
                "min_confidence": 0.6
            }
        )
        
        # Data node for verification history
        verification_history = Config.configure_data_node(
            id="verification_history",
            storage_type="pickle",
            scope="SCENARIO"
        )
        
        # Data node for scenario comparison results
        comparison_results = Config.configure_data_node(
            id="comparison_results",
            storage_type="json",
            scope="SCENARIO"
        )
        
        # Task for threshold analysis
        analysis_task = Config.configure_task(
            id="threshold_analysis",
            function=self._analyze_threshold_impact,
            input=[threshold_config, verification_history],
            output=[comparison_results]
        )
        
        # Scenario configuration
        Config.configure_scenario(
            id="threshold_scenario",
            task_configs=[analysis_task],
            frequency="DAILY"
        )
    
    async def create_scenario(
        self,
        name: str,
        description: str,
        ensemble_threshold: float = 0.7,
        cnn_weight: float = 0.4,
        prnu_weight: float = 0.3,
        metadata_weight: float = 0.3,
        min_confidence: float = 0.6
    ) -> str:
        """
        Create a new threshold scenario for what-if analysis.
        
        Args:
            name: Scenario name
            description: Scenario description
            ensemble_threshold: Minimum ensemble score for AI detection (0.0-1.0)
            cnn_weight: CNN detector weight in ensemble
            prnu_weight: PRNU analyzer weight in ensemble
            metadata_weight: Metadata detector weight in ensemble
            min_confidence: Minimum confidence threshold
        
        Returns:
            scenario_id: Unique scenario identifier
        """
        scenario_id = f"scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name.replace(' ', '_')}"
        
        self.scenarios[scenario_id] = {
            "id": scenario_id,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "config": {
                "ensemble_threshold": ensemble_threshold,
                "cnn_weight": cnn_weight,
                "prnu_weight": prnu_weight,
                "metadata_weight": metadata_weight,
                "min_confidence": min_confidence
            },
            "results": []
        }
        
        return scenario_id
    
    def _analyze_threshold_impact(
        self,
        threshold_config: Dict[str, float],
        verification_history: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Analyze impact of threshold changes on historical verification results.
        
        Args:
            threshold_config: Threshold configuration parameters
            verification_history: Historical verification data
        
        Returns:
            Analysis results with metrics and visualizations
        """
        if verification_history.empty:
            return {
                "status": "no_data",
                "message": "No verification history available for analysis"
            }
        
        # Recalculate decisions with new thresholds
        ensemble_threshold = threshold_config["ensemble_threshold"]
        weights = {
            "cnn": threshold_config["cnn_weight"],
            "prnu": threshold_config["prnu_weight"],
            "metadata": threshold_config["metadata_weight"]
        }
        
        # Analyze decision changes
        original_decisions = verification_history["decision"].tolist()
        recalculated_decisions = []
        decision_changes = 0
        
        for idx, row in verification_history.iterrows():
            # Recalculate ensemble score
            ml_scores = row.get("ml_scores", {})
            if not ml_scores:
                recalculated_decisions.append(row["decision"])
                continue
            
            ensemble_score = (
                weights["cnn"] * ml_scores.get("cnn_score", 0) +
                weights["prnu"] * ml_scores.get("prnu_score", 0) +
                weights["metadata"] * ml_scores.get("metadata_score", 0)
            )
            
            # Apply new threshold
            if ensemble_score >= ensemble_threshold:
                new_decision = "AI_GENERATED"
            else:
                new_decision = row.get("c2pa_result") or row.get("sensor_pki_result") or "UNKNOWN"
            
            recalculated_decisions.append(new_decision)
            if new_decision != row["decision"]:
                decision_changes += 1
        
        # Calculate metrics
        total_verifications = len(verification_history)
        change_percentage = (decision_changes / total_verifications) * 100 if total_verifications > 0 else 0
        
        # Decision distribution
        decision_distribution = pd.Series(recalculated_decisions).value_counts().to_dict()
        original_distribution = pd.Series(original_decisions).value_counts().to_dict()
        
        return {
            "status": "success",
            "threshold_config": threshold_config,
            "total_verifications": total_verifications,
            "decision_changes": decision_changes,
            "change_percentage": round(change_percentage, 2),
            "new_distribution": decision_distribution,
            "original_distribution": original_distribution,
            "recalculated_decisions": recalculated_decisions,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def compare_scenarios(
        self,
        scenario_ids: List[str],
        verification_sample: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple threshold scenarios side-by-side.
        
        Args:
            scenario_ids: List of scenario IDs to compare
            verification_sample: Optional list of job IDs to analyze (uses recent jobs if None)
        
        Returns:
            Comparison results with metrics for each scenario
        """
        if not scenario_ids:
            return {"error": "No scenarios provided for comparison"}
        
        # Get verification jobs for analysis
        if verification_sample:
            jobs = []
            for job_id in verification_sample:
                job = await self.db.get_job_by_job_id(job_id)
                if job:
                    jobs.append(job)
        else:
            # Get recent completed jobs
            jobs = await self._get_recent_jobs(limit=100)
        
        if not jobs:
            return {"error": "No verification jobs available for comparison"}
        
        comparison_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_jobs_analyzed": len(jobs),
            "scenarios": {}
        }
        
        for scenario_id in scenario_ids:
            if scenario_id not in self.scenarios:
                comparison_results["scenarios"][scenario_id] = {"error": "Scenario not found"}
                continue
            
            scenario = self.scenarios[scenario_id]
            config = scenario["config"]
            
            # Recalculate decisions for each job using scenario thresholds
            authentic_count = 0
            ai_generated_count = 0
            unknown_count = 0
            confidence_scores = []
            
            for job in jobs:
                result = job.get("result", {})
                ml_result = result.get("ml_detection", {})
                
                if not ml_result:
                    unknown_count += 1
                    continue
                
                # Recalculate ensemble score
                ensemble_score = (
                    config["cnn_weight"] * ml_result.get("cnn_score", 0) +
                    config["prnu_weight"] * ml_result.get("prnu_score", 0) +
                    config["metadata_weight"] * ml_result.get("metadata_score", 0)
                )
                
                confidence_scores.append(ensemble_score)
                
                # Apply threshold
                if ensemble_score >= config["ensemble_threshold"]:
                    ai_generated_count += 1
                else:
                    # Check other methods
                    c2pa_result = result.get("c2pa_verification", {}).get("status")
                    sensor_pki_result = result.get("sensor_pki_verification", {}).get("status")
                    
                    if c2pa_result == "VALID" or sensor_pki_result == "VALID":
                        authentic_count += 1
                    else:
                        unknown_count += 1
            
            # Calculate metrics
            total = len(jobs)
            comparison_results["scenarios"][scenario_id] = {
                "name": scenario["name"],
                "config": config,
                "metrics": {
                    "authentic": authentic_count,
                    "ai_generated": ai_generated_count,
                    "unknown": unknown_count,
                    "authentic_percentage": round((authentic_count / total) * 100, 2) if total > 0 else 0,
                    "ai_generated_percentage": round((ai_generated_count / total) * 100, 2) if total > 0 else 0,
                    "unknown_percentage": round((unknown_count / total) * 100, 2) if total > 0 else 0,
                    "mean_confidence": round(np.mean(confidence_scores), 3) if confidence_scores else 0,
                    "std_confidence": round(np.std(confidence_scores), 3) if confidence_scores else 0
                }
            }
        
        return comparison_results
    
    async def _get_recent_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent completed verification jobs from database."""
        # Note: This requires adding a method to Database class
        # For now, using a simplified approach
        collection = self.db.db["verification_jobs"]
        cursor = collection.find(
            {"status": "completed"},
            sort=[("created_at", -1)],
            limit=limit
        )
        jobs = await cursor.to_list(length=limit)
        return jobs
    
    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a scenario by ID."""
        return self.scenarios.get(scenario_id)
    
    def list_scenarios(self) -> List[Dict[str, Any]]:
        """List all available scenarios."""
        return list(self.scenarios.values())
    
    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete a scenario."""
        if scenario_id in self.scenarios:
            del self.scenarios[scenario_id]
            return True
        return False


class SPKIATaipyUI:
    """
    Main Taipy GUI application for SPKIA.
    Provides web interface for threshold configuration, scenario management, and visualization.
    """
    
    def __init__(self, scenario_manager: ThresholdScenarioManager):
        self.scenario_manager = scenario_manager
        self.gui = None
        
        # UI State variables
        self.current_page = "Dashboard"
        self.scenario_name = ""
        self.scenario_description = ""
        self.ensemble_threshold = 0.7
        self.cnn_weight = 0.4
        self.prnu_weight = 0.3
        self.metadata_weight = 0.3
        self.min_confidence = 0.6
        self.scenarios_list = []
        self.selected_scenarios = []
        self.comparison_results = {}
        self.analysis_results = {}
        
    def create_gui(self) -> Gui:
        """Create and configure Taipy GUI application."""
        
        # Dashboard page
        dashboard_md = """
# SPKIA - Media Authenticity Verification

<|navbar|>

## Threshold Configuration

Configure AI detection thresholds for verification pipeline.

### Current Configuration
- **Ensemble Threshold**: <|{ensemble_threshold}|slider|min=0.0|max=1.0|step=0.01|>
- **CNN Weight**: <|{cnn_weight}|slider|min=0.0|max=1.0|step=0.05|>
- **PRNU Weight**: <|{prnu_weight}|slider|min=0.0|max=1.0|step=0.05|>
- **Metadata Weight**: <|{metadata_weight}|slider|min=0.0|max=1.0|step=0.05|>
- **Minimum Confidence**: <|{min_confidence}|slider|min=0.0|max=1.0|step=0.01|>

<|Create Scenario|button|on_action=create_scenario|>

---

## Verification Statistics

<|{verification_stats}|chart|type=bar|x=status|y=count|>

"""
        
        # Scenario Management page
        scenarios_md = """
# Scenario Management

<|navbar|>

## Create New Scenario

- **Scenario Name**: <|{scenario_name}|input|>
- **Description**: <|{scenario_description}|input|>

### Threshold Configuration
- **Ensemble Threshold**: <|{ensemble_threshold}|slider|min=0.0|max=1.0|step=0.01|>
- **CNN Weight**: <|{cnn_weight}|slider|min=0.0|max=1.0|step=0.05|>
- **PRNU Weight**: <|{prnu_weight}|slider|min=0.0|max=1.0|step=0.05|>
- **Metadata Weight**: <|{metadata_weight}|slider|min=0.0|max=1.0|step=0.05|>

<|Save Scenario|button|on_action=save_scenario|>

---

## Existing Scenarios

<|{scenarios_list}|table|>

<|Delete Selected|button|on_action=delete_scenario|>

"""
        
        # What-If Analysis page
        analysis_md = """
# What-If Analysis

<|navbar|>

## Scenario Comparison

Select scenarios to compare their impact on verification decisions.

<|{scenarios_list}|selector|value={selected_scenarios}|multiple|>

<|Compare Scenarios|button|on_action=compare_scenarios|>

---

## Comparison Results

<|{comparison_chart}|chart|type=bar|>

### Detailed Metrics

<|{comparison_results}|table|>

"""
        
        # Create multi-page GUI
        pages = {
            "/": dashboard_md,
            "scenarios": scenarios_md,
            "analysis": analysis_md
        }
        
        self.gui = Gui(pages=pages)
        
        # Register callbacks
        self.gui.on_action("create_scenario", self.on_create_scenario)
        self.gui.on_action("save_scenario", self.on_save_scenario)
        self.gui.on_action("delete_scenario", self.on_delete_scenario)
        self.gui.on_action("compare_scenarios", self.on_compare_scenarios)
        
        return self.gui
    
    async def on_create_scenario(self, state: State):
        """Callback for creating a new scenario."""
        if not state.scenario_name:
            notify(state, "error", "Please provide a scenario name")
            return
        
        scenario_id = await self.scenario_manager.create_scenario(
            name=state.scenario_name,
            description=state.scenario_description,
            ensemble_threshold=state.ensemble_threshold,
            cnn_weight=state.cnn_weight,
            prnu_weight=state.prnu_weight,
            metadata_weight=state.metadata_weight,
            min_confidence=state.min_confidence
        )
        
        notify(state, "success", f"Scenario '{state.scenario_name}' created successfully!")
        
        # Reset form
        state.scenario_name = ""
        state.scenario_description = ""
        
        # Refresh scenarios list
        state.scenarios_list = self.scenario_manager.list_scenarios()
    
    async def on_save_scenario(self, state: State):
        """Callback for saving scenario configuration."""
        await self.on_create_scenario(state)
    
    async def on_delete_scenario(self, state: State):
        """Callback for deleting selected scenarios."""
        if not state.selected_scenarios:
            notify(state, "warning", "No scenarios selected")
            return
        
        for scenario_id in state.selected_scenarios:
            self.scenario_manager.delete_scenario(scenario_id)
        
        notify(state, "success", f"Deleted {len(state.selected_scenarios)} scenario(s)")
        
        # Refresh scenarios list
        state.scenarios_list = self.scenario_manager.list_scenarios()
        state.selected_scenarios = []
    
    async def on_compare_scenarios(self, state: State):
        """Callback for comparing scenarios."""
        if not state.selected_scenarios:
            notify(state, "warning", "Please select at least one scenario to compare")
            return
        
        results = await self.scenario_manager.compare_scenarios(state.selected_scenarios)
        
        if "error" in results:
            notify(state, "error", results["error"])
            return
        
        state.comparison_results = results
        notify(state, "success", f"Compared {len(state.selected_scenarios)} scenarios")
    
    def run(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Run the Taipy GUI application."""
        if not self.gui:
            self.create_gui()
        
        self.gui.run(
            host=host,
            port=port,
            debug=debug,
            title="SPKIA - Media Authenticity Verification"
        )


# Factory function for integration with FastAPI
async def create_taipy_ui(db: Database, verification_service: VerificationService) -> SPKIATaipyUI:
    """
    Factory function to create Taipy UI instance.
    
    Args:
        db: Database instance
        verification_service: Verification service instance
    
    Returns:
        Configured SPKIATaipyUI instance
    """
    scenario_manager = ThresholdScenarioManager(db, verification_service)
    taipy_ui = SPKIATaipyUI(scenario_manager)
    return taipy_ui
