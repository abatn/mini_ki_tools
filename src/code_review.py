import subprocess
import json
import os
from typing import Dict, List, Any
from dependency_installer import install_packages

class CodeReviewAgent:
    def __init__(self):
        self.dependencies = {
            'bandit': 'bandit',
            'radon': 'radon',
            'pylint': 'pylint'
        }
        
    def install_required_tools(self):
        """Install required tools for code review"""
        for tool_name, package_name in self.dependencies.items():
            try:
                __import__(tool_name)
            except ImportError:
                print(f"Installing {tool_name}...")
                install_dependency(package_name)
                
    def run_security_scan(self, file_path: str) -> Dict[str, Any]:
        """Run security scan using Bandit"""
        try:
            result = subprocess.run(
                ['bandit', '-r', file_path, '-f', 'json'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode in [0, 1]:  # Bandit returns 0 for no issues, 1 for issues found
                return json.loads(result.stdout)
            else:
                return {'error': f'Bandit scan failed: {result.stderr}'}
        except subprocess.TimeoutExpired:
            return {'error': 'Bandit scan timed out'}
        except Exception as e:
            return {'error': f'Bandit scan error: {str(e)}'}
    
    def run_performance_scan(self, file_path: str) -> Dict[str, Any]:
        """Run performance analysis using Radon"""
        try:
            result = subprocess.run(
                ['radon', 'raw', file_path, '-s'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {'output': result.stdout}
            else:
                return {'error': f'Radon scan failed: {result.stderr}'}
        except subprocess.TimeoutExpired:
            return {'error': 'Radon scan timed out'}
        except Exception as e:
            return {'error': f'Radon scan error: {str(e)}'}
    
    def run_style_scan(self, file_path: str) -> Dict[str, Any]:
        """Run style analysis using Pylint"""
        try:
            result = subprocess.run(
                ['pylint', '--output-format=json', file_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode in [0, 1]:  # Pylint returns 0 for no issues, 1 for issues found
                if result.stdout.strip():
                    return json.loads(result.stdout)
                else:
                    return {'messages': []}
            else:
                return {'error': f'Pylint scan failed: {result.stderr}'}
        except subprocess.TimeoutExpired:
            return {'error': 'Pylint scan timed out'}
        except Exception as e:
            return {'error': f'Pylint scan error: {str(e)}'}
    
    def generate_review_report(self, file_path: str) -> Dict[str, Any]:
        """Generate complete code review report"""
        # Install required tools
        self.install_required_tools()
        
        # Run all scans
        security_results = self.run_security_scan(file_path)
        performance_results = self.run_performance_scan(file_path)
        style_results = self.run_style_scan(file_path)
        
        # Analyze and categorize issues
        issues = []
        
        # Security issues
        if 'error' not in security_results:
            for issue in security_results.get('results', []):
                issues.append({
                    'type': 'security',
                    'category': 'HIGH',
                    'message': issue.get('issue_text', ''),
                    'file': issue.get('filename', file_path),
                    'line': issue.get('line_number', 0)
                })
        
        # Performance issues (if any)
        if 'error' not in performance_results and performance_results.get('output'):
            issues.append({
                'type': 'performance',
                'category': 'MEDIUM',
                'message': 'Performance issues found',
                'file': file_path
            })
        
        # Style issues
        if 'error' not in style_results:
            for issue in style_results.get('messages', []):
                issues.append({
                    'type': 'style',
                    'category': 'LOW',
                    'message': issue.get('message', ''),
                    'file': issue.get('path', file_path),
                    'line': issue.get('line', 0)
                })
        
        return {
            'file': file_path,
            'issues': issues,
            'summary': {
                'total_issues': len(issues),
                'high_severity': len([i for i in issues if i['category'] == 'HIGH']),
                'medium_severity': len([i for i in issues if i['category'] == 'MEDIUM']),
                'low_severity': len([i for i in issues if i['category'] == 'LOW'])
            }
        }
