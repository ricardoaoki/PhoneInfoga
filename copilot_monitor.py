#!/usr/bin/env python3
"""
Automated Copilot Task Monitor - Runs periodically to check task progress
"""

import time
import json
import os
import sys
from datetime import datetime, timedelta
from copilot_agent import GitHubCopilotAgent


def load_monitor_config():
    """Load monitoring configuration."""
    config_file = "copilot_monitor_config.json"
    default_config = {
        "check_interval_minutes": 30,
        "auto_delegate_new_tasks": False,
        "notification_webhook": None,
        "max_monitoring_hours": 24,
        "report_file": "copilot_monitor_report.json"
    }
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            # Merge with defaults
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    else:
        # Create default config file
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        return default_config


def save_monitor_report(report_data):
    """Save monitoring report to file."""
    config = load_monitor_config()
    report_file = config.get("report_file", "copilot_monitor_report.json")
    
    # Load existing reports
    reports = []
    if os.path.exists(report_file):
        with open(report_file, 'r') as f:
            reports = json.load(f)
    
    # Add new report
    reports.append(report_data)
    
    # Keep only last 100 reports
    if len(reports) > 100:
        reports = reports[-100:]
    
    # Save updated reports
    with open(report_file, 'w') as f:
        json.dump(reports, f, indent=2)


def continuous_monitor():
    """Run continuous monitoring of Copilot tasks."""
    config = load_monitor_config()
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable required for monitoring")
        return
    
    agent = GitHubCopilotAgent("ricardoaoki", "PhoneInfoga", github_token)
    
    print(f"🤖 Starting continuous Copilot task monitoring...")
    print(f"⏰ Check interval: {config['check_interval_minutes']} minutes")
    print(f"🕒 Max monitoring time: {config['max_monitoring_hours']} hours")
    print("📊 Press Ctrl+C to stop\n")
    
    start_time = datetime.now()
    max_duration = timedelta(hours=config['max_monitoring_hours'])
    check_interval = timedelta(minutes=config['check_interval_minutes'])
    
    try:
        while True:
            current_time = datetime.now()
            
            # Check if we've exceeded max monitoring time
            if current_time - start_time > max_duration:
                print(f"⏰ Maximum monitoring time ({config['max_monitoring_hours']} hours) reached. Stopping.")
                break
            
            print(f"🔍 Checking task progress at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Monitor progress
            progress = agent.monitor_progress()
            
            # Auto-delegate new tasks if enabled
            if config.get('auto_delegate_new_tasks', False):
                print("\n🔄 Auto-delegating new tasks...")
                new_tasks = agent.delegate_tasks()
                if new_tasks:
                    print(f"✅ Auto-delegated {len(new_tasks)} new tasks")
                    progress['new_tasks_delegated'] = len(new_tasks)
                else:
                    progress['new_tasks_delegated'] = 0
            
            # Prepare report
            report = {
                "timestamp": current_time.isoformat(),
                "progress": progress,
                "monitoring_duration_hours": (current_time - start_time).total_seconds() / 3600
            }
            
            # Save report
            save_monitor_report(report)
            
            # Show progress summary
            if progress['total'] > 0:
                print(f"\n📈 Summary:")
                print(f"   ✅ Completed: {progress['closed']}/{progress['total']} ({progress['completion_rate']:.1f}%)")
                print(f"   🔄 In Progress: {progress['in_progress']}")
                print(f"   ⏳ Open: {progress['open']}")
                
                # Check for recent completions
                if progress['closed'] > 0:
                    print(f"\n🎉 {progress['closed']} task(s) have been completed by Copilot!")
            
            print(f"\n⏰ Next check in {config['check_interval_minutes']} minutes...")
            print("-" * 50)
            
            # Wait for next check
            time.sleep(check_interval.total_seconds())
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
        end_time = datetime.now()
        total_duration = end_time - start_time
        print(f"📊 Total monitoring duration: {total_duration}")
        
        # Final progress check
        print("\n🔍 Final progress check:")
        final_progress = agent.monitor_progress()
        
        # Save final report
        final_report = {
            "timestamp": end_time.isoformat(),
            "progress": final_progress,
            "monitoring_duration_hours": total_duration.total_seconds() / 3600,
            "session_type": "final"
        }
        save_monitor_report(final_report)


def show_monitor_history():
    """Show monitoring history and trends."""
    config = load_monitor_config()
    report_file = config.get("report_file", "copilot_monitor_report.json")
    
    if not os.path.exists(report_file):
        print("📭 No monitoring history found")
        return
    
    with open(report_file, 'r') as f:
        reports = json.load(f)
    
    if not reports:
        print("📭 No monitoring reports found")
        return
    
    print(f"📊 Monitoring History ({len(reports)} reports)\n")
    
    # Show recent reports
    recent_reports = reports[-10:]  # Last 10 reports
    
    for i, report in enumerate(recent_reports, 1):
        timestamp = datetime.fromisoformat(report['timestamp'])
        progress = report['progress']
        
        print(f"{i}. {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if progress['total'] > 0:
            print(f"   📈 Progress: {progress['closed']}/{progress['total']} ({progress['completion_rate']:.1f}%)")
            print(f"   🔄 In Progress: {progress['in_progress']}, ⏳ Open: {progress['open']}")
        else:
            print("   📭 No tasks")
        print()
    
    # Show trends
    if len(reports) >= 2:
        first_report = reports[0]
        last_report = reports[-1]
        
        first_completed = first_report['progress']['closed']
        last_completed = last_report['progress']['closed']
        completion_increase = last_completed - first_completed
        
        print(f"📈 Trends:")
        print(f"   🎯 Tasks completed since monitoring started: {completion_increase}")
        print(f"   ⏱️  Total monitoring time: {last_report.get('monitoring_duration_hours', 0):.1f} hours")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 copilot_monitor.py start     - Start continuous monitoring")
        print("  python3 copilot_monitor.py history   - Show monitoring history")
        print("  python3 copilot_monitor.py config    - Show current configuration")
        return
    
    command = sys.argv[1]
    
    if command == "start":
        continuous_monitor()
    elif command == "history":
        show_monitor_history()
    elif command == "config":
        config = load_monitor_config()
        print("📋 Current Monitor Configuration:")
        for key, value in config.items():
            print(f"   {key}: {value}")
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()