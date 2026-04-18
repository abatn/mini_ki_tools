import subprocess
import sys
import json
from typing import Dict, List

class SecurityScanner:
    def __init__(self):
        self.vulnerabilities = []
    
    def scan_with_bandit(self, filepath: str) -> List[Dict]:
        """Scan Python files for security vulnerabilities using Bandit"""
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'bandit'], 
                         capture_output=True, check=True)
            
            result = subprocess.run([
                sys.executable, '-m', 'bandit', '-r', filepath, '-f', 'json', '--exit-zero'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode in [0, 1]:
                scan_results = json.loads(result.stdout)
                vulnerabilities = []
                for issue in scan_results.get('results', []):
                    vulnerabilities.append({
                        'file': issue['filename'],
                        'line': issue['line_number'],
                        'severity': issue['issue_severity'].upper(),
                        'confidence': issue['issue_confidence'].upper(),
                        'code': issue['code'],
                        'issue': issue['issue_text'],
                        'category': 'SECURITY',
                        'criticality': 'HIGH' if issue['issue_severity'].upper() in ['HIGH', 'CRITICAL'] else 'MEDIUM'
                    })
                return vulnerabilities
            return []
        except Exception as e:
            print(f"Bandit scan failed: {e}")
            return []
    
    def scan_file(self, filepath: str) -> Dict:
        """Run all scans on a file"""
        results = {
            'file': filepath,
            'security': self.scan_with_bandit(filepath),
            'total_issues': 0
        }
        results['total_issues'] = len(results['security'])
        return results
    
    def generate_report(self, file_results: Dict) -> str:
        """Generate a formatted report"""
        report = f"\n=== Code Review Report for {file_results['file']} ===\n"
        report += f"Total Issues: {file_results['total_issues']}\n\n"
        
        for issue in file_results['security']:
            report += f"[{issue['criticality']}] {issue['category']}: {issue['issue']}\n"
            report += f"  File: {issue['file']}:{issue['line']}\n"
            report += f"  Code: {issue['code']}\n\n"
        return report
