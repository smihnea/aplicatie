#!/usr/bin/env python3
"""
YAML Validation Script for GitHub Actions Workflow
Validates the GitHub Actions workflow file for syntax errors.
"""

import yaml
import sys
from pathlib import Path

def validate_yaml_file(file_path):
    """Validate a YAML file for syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            yaml.safe_load(content)
        return True, None
    except yaml.YAMLError as e:
        return False, f"YAML syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def main():
    """Main validation function."""
    workflow_file = Path(".github/workflows/build-executables.yml")
    
    print("🔍 GitHub Actions Workflow Validation")
    print("=" * 50)
    
    if not workflow_file.exists():
        print(f"❌ Workflow file not found: {workflow_file}")
        return False
    
    print(f"📁 Validating: {workflow_file}")
    
    is_valid, error = validate_yaml_file(workflow_file)
    
    if is_valid:
        print("✅ YAML syntax is valid!")
        print("\n📋 Next steps:")
        print("1. Commit the workflow file")
        print("2. Push to GitHub")
        print("3. Check the Actions tab for build results")
        return True
    else:
        print(f"❌ {error}")
        print("\n🔧 To fix:")
        print("1. Check the YAML syntax around the error line")
        print("2. Ensure proper indentation (spaces, not tabs)")
        print("3. Check for unescaped special characters")
        print("4. Validate multi-line strings are properly formatted")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)