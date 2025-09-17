#!/usr/bin/env python3
"""
Configuration loader for CI thresholds and monitoring setup.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class CIThresholds:
    """Dynamic CI thresholds from configuration."""
    min_parity_rate: float
    max_p95_latency_ms: float
    max_avg_latency_ms: float
    min_success_rate: float
    target_accuracy: Optional[float] = None
    max_regression_factor: Optional[float] = None

@dataclass
class AlertConfig:
    """Alert configuration."""
    slack_webhook_url: Optional[str]
    notification_teams: list
    critical_conditions: list

def load_ci_config(
    config_path: Optional[str] = None,
    environment: str = "development"
) -> Dict[str, Any]:
    """
    Load CI configuration from YAML file.

    Args:
        config_path: Path to configuration file (default: .github/ci-thresholds.yml)
        environment: Environment name for threshold overrides

    Returns:
        Loaded configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / ".github" / "ci-thresholds.yml"

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        # Fallback to default configuration
        config = get_default_config()
    except yaml.YAMLError as e:
        print(f"Warning: Failed to parse config file: {e}")
        config = get_default_config()

    # Apply environment-specific overrides
    if environment in config.get("environments", {}):
        env_config = config["environments"][environment]
        config["quality_gates"].update(env_config)
        if "performance" in env_config:
            config["performance"].update(env_config)

    return config

def get_ci_thresholds(
    config_path: Optional[str] = None,
    environment: Optional[str] = None
) -> CIThresholds:
    """
    Get CI thresholds for the current environment.

    Args:
        config_path: Path to configuration file
        environment: Environment name (defaults to CI_ENVIRONMENT env var)

    Returns:
        CIThresholds object with loaded values
    """
    if environment is None:
        environment = os.getenv("CI_ENVIRONMENT", "development")

    config = load_ci_config(config_path, environment)

    quality_gates = config["quality_gates"]
    performance = config["performance"]

    return CIThresholds(
        min_parity_rate=quality_gates["min_parity_rate"],
        max_p95_latency_ms=performance["max_p95_latency_ms"],
        max_avg_latency_ms=performance["max_avg_latency_ms"],
        min_success_rate=quality_gates["min_success_rate"],
        target_accuracy=quality_gates.get("target_accuracy"),
        max_regression_factor=performance.get("max_regression_factor")
    )

def get_alert_config(config_path: Optional[str] = None) -> AlertConfig:
    """Get alert configuration."""
    config = load_ci_config(config_path)
    alerts = config.get("alerts", {})

    return AlertConfig(
        slack_webhook_url=alerts.get("slack_webhook_url"),
        notification_teams=alerts.get("notification_teams", []),
        critical_conditions=alerts.get("critical_conditions", [])
    )

def check_critical_conditions(metrics: Dict[str, Any], config_path: Optional[str] = None) -> list:
    """
    Check if any critical alert conditions are met.

    Args:
        metrics: Metrics dictionary from CI monitor
        config_path: Path to configuration file

    Returns:
        List of triggered critical conditions
    """
    alert_config = get_alert_config(config_path)
    triggered_conditions = []

    for condition in alert_config.critical_conditions:
        try:
            # Simple condition evaluation
            # Format: "metric_name < value" or "metric_name > value"
            if "<" in condition:
                metric_name, threshold = condition.split("<")
                metric_name = metric_name.strip()
                threshold = float(threshold.strip())
                if metrics.get(metric_name, float('inf')) < threshold:
                    triggered_conditions.append(condition)
            elif ">" in condition:
                metric_name, threshold = condition.split(">")
                metric_name = metric_name.strip()
                threshold = float(threshold.strip())
                if metrics.get(metric_name, 0) > threshold:
                    triggered_conditions.append(condition)
        except (ValueError, AttributeError):
            print(f"Warning: Invalid condition format: {condition}")

    return triggered_conditions

def send_alert(message: str, config_path: Optional[str] = None) -> bool:
    """
    Send alert notification.

    Args:
        message: Alert message to send
        config_path: Path to configuration file

    Returns:
        True if alert was sent successfully
    """
    alert_config = get_alert_config(config_path)

    if alert_config.slack_webhook_url:
        try:
            import requests
            response = requests.post(
                alert_config.slack_webhook_url,
                json={"text": message},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False

    # Fallback: print to console
    print(f"ALERT: {message}")
    return True

def get_default_config() -> Dict[str, Any]:
    """Get default configuration when config file is not available."""
    return {
        "quality_gates": {
            "min_parity_rate": 0.8,
            "min_success_rate": 0.95,
            "target_accuracy": 0.8
        },
        "performance": {
            "max_p95_latency_ms": 50.0,
            "max_avg_latency_ms": 20.0,
            "max_regression_factor": 1.5
        },
        "environments": {},
        "feature_flags": {
            "normalization_implementation": "factory",
            "factory_rollout_percentage": 100,
            "enable_dual_processing": True,
            "log_implementation_choice": True
        },
        "alerts": {
            "slack_webhook_url": None,
            "notification_teams": [],
            "critical_conditions": [
                "parity_rate < 0.5",
                "factory_success_rate < 0.9",
                "factory_p95_latency_ms > 100"
            ]
        }
    }

if __name__ == "__main__":
    """Test configuration loading."""
    import json

    print("🔧 Testing CI Configuration Loader")
    print("=" * 50)

    # Test loading configuration
    config = load_ci_config()
    print(f"✅ Loaded configuration: {len(config)} sections")

    # Test thresholds for different environments
    for env in ["development", "staging", "production"]:
        thresholds = get_ci_thresholds(environment=env)
        print(f"📊 {env.title()} thresholds:")
        print(f"  Parity: {thresholds.min_parity_rate:.1%}")
        print(f"  P95 Latency: {thresholds.max_p95_latency_ms}ms")
        print(f"  Avg Latency: {thresholds.max_avg_latency_ms}ms")
        print()

    # Test alert configuration
    alert_config = get_alert_config()
    print(f"🚨 Alert configuration:")
    print(f"  Teams: {alert_config.notification_teams}")
    print(f"  Critical conditions: {len(alert_config.critical_conditions)}")

    # Test critical condition checking
    test_metrics = {
        "parity_rate": 0.4,
        "factory_success_rate": 0.85,
        "factory_p95_latency_ms": 120.0
    }

    triggered = check_critical_conditions(test_metrics)
    print(f"\n🔥 Critical conditions triggered: {len(triggered)}")
    for condition in triggered:
        print(f"  - {condition}")