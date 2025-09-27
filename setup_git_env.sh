#!/bin/bash

# Setup Git Environment for IDEs
# This script ensures git is properly configured and available

echo "🔧 Setting up Git environment for IDEs..."

# Check if git is available
if command -v git &> /dev/null; then
    echo "✅ Git found at: $(which git)"
    echo "✅ Git version: $(git --version)"
else
    echo "❌ Git not found in PATH"
    exit 1
fi

# Add git to PATH in shell profiles
echo "📝 Updating shell profiles..."

# For zsh (default on macOS)
if [ -f ~/.zshrc ]; then
    if ! grep -q "/usr/bin" ~/.zshrc; then
        echo 'export PATH="/usr/bin:/usr/local/bin:$PATH"' >> ~/.zshrc
        echo "✅ Updated ~/.zshrc"
    fi
else
    echo 'export PATH="/usr/bin:/usr/local/bin:$PATH"' > ~/.zshrc
    echo "✅ Created ~/.zshrc"
fi

# For bash (backup)
if [ -f ~/.bash_profile ]; then
    if ! grep -q "/usr/bin" ~/.bash_profile; then
        echo 'export PATH="/usr/bin:/usr/local/bin:$PATH"' >> ~/.bash_profile
        echo "✅ Updated ~/.bash_profile"
    fi
else
    echo 'export PATH="/usr/bin:/usr/local/bin:$PATH"' > ~/.bash_profile
    echo "✅ Created ~/.bash_profile"
fi

# Set global git config if not set
if [ -z "$(git config --global user.name)" ]; then
    echo "⚠️  Git user.name not set. Please run:"
    echo "   git config --global user.name 'Your Name'"
fi

if [ -z "$(git config --global user.email)" ]; then
    echo "⚠️  Git user.email not set. Please run:"
    echo "   git config --global user.email 'your.email@example.com'"
fi

echo ""
echo "🎉 Git environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Restart your IDE"
echo "2. If using VS Code, set Git path to: /usr/bin/git"
echo "3. If still having issues, try restarting your terminal"
echo ""
echo "🔍 Git executable location: $(which git)"
echo "📁 Current directory git status:"
git status --porcelain | head -5
