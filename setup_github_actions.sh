#!/bin/bash

# GitHub Actions Setup Script for Excel Product Extractor
# This script helps you set up the automated Windows executable builds

echo "🚀 Setting up GitHub Actions for Windows Executable Builds"
echo "=========================================================="
echo

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "⚠️  This directory is not a git repository."
    echo "   Initialize git first:"
    echo "   git init"
    echo "   git remote add origin https://github.com/yourusername/your-repo.git"
    echo
    exit 1
fi

# Check if GitHub Actions workflow exists
if [ ! -f ".github/workflows/build-executables.yml" ]; then
    echo "❌ GitHub Actions workflow not found!"
    echo "   The workflow file should be at: .github/workflows/build-executables.yml"
    exit 1
fi

echo "✅ GitHub Actions workflow found"
echo

# Check if we have required files
echo "📋 Checking required files..."
required_files=(
    "start_app.py"
    "excel_processor.spec"
    "requirements.txt"
    "src/gui/modern_window.py"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo
    echo "⚠️  Some required files are missing. Please make sure all files exist."
    exit 1
fi

echo
echo "📤 Ready to push to GitHub!"
echo

# Get current git status
echo "Current git status:"
echo "==================="
git status --short
echo

# Check if there are changes to commit
if [ -n "$(git status --porcelain)" ]; then
    echo "💾 You have uncommitted changes."
    echo
    echo "Recommended commands:"
    echo "1. git add .github/ excel_processor.spec GITHUB_ACTIONS_SETUP.md setup_github_actions.sh"
    echo "2. git commit -m 'Add GitHub Actions for automated Windows executable builds'"
    echo "3. git push origin main"
    echo
    
    read -p "🤔 Would you like me to run these commands for you? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📝 Adding files..."
        git add .github/ excel_processor.spec GITHUB_ACTIONS_SETUP.md setup_github_actions.sh
        
        echo "💾 Committing..."
        git commit -m "Add GitHub Actions for automated Windows executable builds

- Automated builds for Windows (.exe), macOS, and Linux
- Builds trigger on push to main branch and pull requests
- Creates GitHub releases when tags are pushed
- Includes comprehensive documentation and setup guides"
        
        echo "📤 Pushing to GitHub..."
        git push origin main || git push origin master
        
        echo
        echo "🎉 SUCCESS! GitHub Actions workflow has been pushed!"
        echo
        echo "📋 Next steps:"
        echo "1. Go to your GitHub repository"
        echo "2. Click the 'Actions' tab"
        echo "3. Watch your first build run!"
        echo "4. Download the Windows executable from 'Artifacts' when complete"
        echo
        echo "🏷️  To create a release:"
        echo "   git tag v1.0.0"
        echo "   git push origin v1.0.0"
        echo
    else
        echo "👍 No problem! Run the commands manually when you're ready."
    fi
else
    echo "✅ All changes are already committed."
    echo
    echo "📤 Push to GitHub with:"
    echo "   git push origin main"
    echo
    echo "🏷️  Or create a release:"
    echo "   git tag v1.0.0"
    echo "   git push origin v1.0.0"
fi

echo
echo "📖 For detailed instructions, see: GITHUB_ACTIONS_SETUP.md"
echo "🎯 Your Windows executables will be built automatically in the cloud!"