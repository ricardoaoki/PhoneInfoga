#!/usr/bin/env python3
"""
GitHub Copilot Task Delegation and Monitoring System
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse


class GitHubCopilotAgent:
    """
    A system for delegating tasks to GitHub Copilot and monitoring progress.
    """
    
    def __init__(self, repo_owner: str, repo_name: str, github_token: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PhoneInfoga-Copilot-Agent"
        }
        self.task_storage_file = "copilot_tasks.json"
        
    def load_tasks(self) -> Dict:
        """Load existing tasks from storage."""
        if os.path.exists(self.task_storage_file):
            with open(self.task_storage_file, 'r') as f:
                return json.load(f)
        return {"tasks": []}
    
    def save_tasks(self, tasks: Dict):
        """Save tasks to storage."""
        with open(self.task_storage_file, 'w') as f:
            json.dump(tasks, f, indent=2)
    
    def identify_code_issues(self) -> List[Dict]:
        """
        Identify potential coding issues that could be delegated to Copilot.
        This scans the codebase for common issues, TODOs, and improvement opportunities.
        """
        issues = []
        
        # Scan Python files for issues
        python_files = ["phoneinfoga.py"]
        for file_path in python_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        # Look for syntax warnings (escape sequences)
                        if 'invalid escape sequence' in line or '\\' in line and 'print(' in line:
                            issues.append({
                                "type": "syntax_warning",
                                "file": file_path,
                                "line": i,
                                "description": "Fix invalid escape sequences in string literals",
                                "priority": "medium",
                                "code_snippet": line.strip()
                            })
                        
                        # Look for TODO comments
                        if 'TODO' in line.upper() or 'FIXME' in line.upper():
                            issues.append({
                                "type": "todo",
                                "file": file_path,
                                "line": i,
                                "description": "Address TODO/FIXME comment",
                                "priority": "low",
                                "code_snippet": line.strip()
                            })
                        
                        # Look for error handling improvements
                        if 'except:' in line and 'pass' in lines[i] if i < len(lines) else False:
                            issues.append({
                                "type": "error_handling",
                                "file": file_path,
                                "line": i,
                                "description": "Improve generic exception handling",
                                "priority": "high",
                                "code_snippet": line.strip()
                            })
        
        return issues
    
    def create_github_issue(self, issue: Dict) -> Optional[int]:
        """Create a GitHub issue for a coding task."""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues"
        
        title = f"[Copilot Task] {issue['description']}"
        body = f"""
## Task Description
{issue['description']}

## File
`{issue['file']}` (line {issue['line']})

## Code Snippet
```python
{issue['code_snippet']}
```

## Priority
{issue['priority']}

## Task Type
{issue['type']}

---
*This issue was automatically created by the Copilot Task Delegation System*
*Assigned to: GitHub Copilot*
"""
        
        data = {
            "title": title,
            "body": body,
            "labels": ["copilot-task", f"priority-{issue['priority']}", f"type-{issue['type']}"]
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            if response.status_code == 201:
                issue_data = response.json()
                return issue_data["number"]
            else:
                print(f"Failed to create issue: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error creating GitHub issue: {e}")
            return None
    
    def delegate_tasks(self) -> List[Dict]:
        """Identify and delegate tasks to GitHub Copilot."""
        print("🔍 Identifying potential coding tasks...")
        issues = self.identify_code_issues()
        
        if not issues:
            print("✅ No issues found that need delegation.")
            return []
        
        print(f"📋 Found {len(issues)} potential tasks")
        
        delegated_tasks = []
        existing_tasks = self.load_tasks()
        
        for issue in issues:
            print(f"\n📝 Processing: {issue['description']}")
            
            # Check if this task was already delegated
            task_key = f"{issue['file']}:{issue['line']}:{issue['type']}"
            already_exists = any(
                task.get('task_key') == task_key 
                for task in existing_tasks.get('tasks', [])
            )
            
            if already_exists:
                print("   ⏭️  Task already delegated, skipping...")
                continue
            
            # Create GitHub issue
            issue_number = self.create_github_issue(issue)
            
            if issue_number:
                task = {
                    "task_key": task_key,
                    "issue_number": issue_number,
                    "created_at": datetime.now().isoformat(),
                    "status": "delegated",
                    "issue_details": issue,
                    "github_url": f"https://github.com/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
                }
                delegated_tasks.append(task)
                print(f"   ✅ Created GitHub issue #{issue_number}")
            else:
                print(f"   ❌ Failed to create GitHub issue")
        
        # Save delegated tasks
        if delegated_tasks:
            existing_tasks["tasks"].extend(delegated_tasks)
            self.save_tasks(existing_tasks)
        
        return delegated_tasks
    
    def get_issue_status(self, issue_number: int) -> Tuple[str, Dict]:
        """Get the current status of a GitHub issue."""
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                issue_data = response.json()
                return issue_data["state"], issue_data
            else:
                return "unknown", {}
        except Exception as e:
            print(f"Error getting issue status: {e}")
            return "error", {}
    
    def monitor_progress(self) -> Dict:
        """Monitor progress on all delegated tasks."""
        print("📊 Monitoring Copilot task progress...\n")
        
        tasks_data = self.load_tasks()
        tasks = tasks_data.get("tasks", [])
        
        if not tasks:
            print("📭 No delegated tasks to monitor.")
            return {"total": 0, "open": 0, "closed": 0, "in_progress": 0}
        
        status_counts = {"open": 0, "closed": 0, "in_progress": 0}
        updated_tasks = []
        
        for task in tasks:
            issue_number = task["issue_number"]
            print(f"🔍 Checking issue #{issue_number}...")
            
            state, issue_data = self.get_issue_status(issue_number)
            
            if state == "closed":
                status_counts["closed"] += 1
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat()
                print(f"   ✅ Completed: {task['issue_details']['description']}")
            elif state == "open":
                # Check for activity (comments, labels, etc.)
                comments_count = issue_data.get("comments", 0)
                if comments_count > 0:
                    status_counts["in_progress"] += 1
                    task["status"] = "in_progress"
                    print(f"   🔄 In Progress: {task['issue_details']['description']}")
                else:
                    status_counts["open"] += 1
                    task["status"] = "open"
                    print(f"   ⏳ Open: {task['issue_details']['description']}")
            else:
                status_counts["open"] += 1
                print(f"   ❓ Unknown status for: {task['issue_details']['description']}")
            
            updated_tasks.append(task)
        
        # Save updated task status
        tasks_data["tasks"] = updated_tasks
        tasks_data["last_monitored"] = datetime.now().isoformat()
        self.save_tasks(tasks_data)
        
        # Print summary
        total = len(tasks)
        print(f"\n📈 Progress Summary:")
        print(f"   Total Tasks: {total}")
        print(f"   Open: {status_counts['open']}")
        print(f"   In Progress: {status_counts['in_progress']}")
        print(f"   Completed: {status_counts['closed']}")
        
        completion_rate = (status_counts['closed'] / total * 100) if total > 0 else 0
        print(f"   Completion Rate: {completion_rate:.1f}%")
        
        return {
            "total": total,
            **status_counts,
            "completion_rate": completion_rate
        }
    
    def list_tasks(self):
        """List all delegated tasks and their current status."""
        tasks_data = self.load_tasks()
        tasks = tasks_data.get("tasks", [])
        
        if not tasks:
            print("📭 No delegated tasks found.")
            return
        
        print(f"📋 Delegated Tasks ({len(tasks)} total):\n")
        
        for i, task in enumerate(tasks, 1):
            status_emoji = {
                "delegated": "📝",
                "open": "⏳",
                "in_progress": "🔄",
                "completed": "✅"
            }.get(task["status"], "❓")
            
            print(f"{i}. {status_emoji} Issue #{task['issue_number']}")
            print(f"   📁 {task['issue_details']['file']}:{task['issue_details']['line']}")
            print(f"   📋 {task['issue_details']['description']}")
            print(f"   🏷️  Priority: {task['issue_details']['priority']}")
            print(f"   🔗 {task['github_url']}")
            print()


def main():
    parser = argparse.ArgumentParser(description="GitHub Copilot Task Delegation and Monitoring System")
    parser.add_argument("--repo-owner", default="ricardoaoki", help="GitHub repository owner")
    parser.add_argument("--repo-name", default="PhoneInfoga", help="GitHub repository name")
    parser.add_argument("--github-token", help="GitHub API token (or set GITHUB_TOKEN env var)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Delegate command
    delegate_parser = subparsers.add_parser("delegate", help="Identify and delegate tasks to Copilot")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor progress on delegated tasks")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all delegated tasks")
    
    args = parser.parse_args()
    
    # Get GitHub token
    github_token = args.github_token or os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GitHub token required. Use --github-token or set GITHUB_TOKEN environment variable.")
        return
    
    agent = GitHubCopilotAgent(args.repo_owner, args.repo_name, github_token)
    
    if args.command == "delegate":
        print("🚀 Starting task delegation to GitHub Copilot...\n")
        delegated = agent.delegate_tasks()
        if delegated:
            print(f"\n✅ Successfully delegated {len(delegated)} tasks to GitHub Copilot!")
        else:
            print("\n📝 No new tasks to delegate.")
            
    elif args.command == "monitor":
        agent.monitor_progress()
        
    elif args.command == "list":
        agent.list_tasks()
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()