# Development Workflow Guide

## 🌳 **Git Branching Strategy**

This project uses a **Git Flow** inspired branching model for organized development:

### **Branch Structure:**

```
main (production)
├── develop (integration)
│   ├── feature/new-feature-name
│   ├── feature/another-feature
│   └── bugfix/fix-something
└── hotfix/critical-fix (emergency fixes to main)
```

### **Branch Purposes:**

- **`main`**: Production-ready code, stable releases only
- **`develop`**: Integration branch where features come together  
- **`feature/*`**: New features and enhancements
- **`bugfix/*`**: Bug fixes for develop branch
- **`hotfix/*`**: Critical fixes that go directly to main

## 🚀 **Development Workflow**

### **1. Starting New Work**

```bash
# Always start from latest develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/my-new-feature

# Or for bug fixes:
git checkout -b bugfix/fix-table-sorting
```

### **2. Working on Features**

```bash
# Make your changes
# Test locally with: ./scripts/build-linux.sh

# Commit frequently with clear messages
git add .
git commit -m "Add device reconnection logic

- Implement auto-retry for failed connections
- Add exponential backoff timing
- Update UI feedback for connection states"

# Push to your branch
git push -u origin feature/my-new-feature
```

### **3. Getting Code to Develop**

```bash
# When feature is ready, create Pull Request:
# GitHub → New Pull Request → feature/my-new-feature → develop

# After PR approval and merge, clean up:
git checkout develop
git pull origin develop
git branch -d feature/my-new-feature
```

### **4. Releasing to Main**

```bash
# When develop is stable and ready for release:
# GitHub → New Pull Request → develop → main

# After merge to main, tag the release:
git checkout main
git pull origin main
git tag -a v1.2.0 -m "Release version 1.2.0

- Added automatic device reconnection
- Fixed table sorting issues  
- Improved Windows compatibility
- Enhanced error handling"

git push origin v1.2.0
```

## 🔧 **CI/CD Integration**

### **Automated Testing:**
- **All branches**: Code quality checks (black, flake8)
- **develop + PRs**: Test builds (no release)
- **main**: Full release builds + GitHub releases

### **Release Automation:**
- Pushing tags to `main` triggers automatic releases
- Both Windows and Linux executables are built
- Release notes are auto-generated from commits

## 📋 **Best Practices**

### **Branch Naming:**
```bash
feature/add-ssh-key-auth          # ✅ Clear, descriptive
feature/device-state-detection    # ✅ Feature purpose obvious
bugfix/windows-path-separator     # ✅ Bug being fixed clear
hotfix/security-vulnerability     # ✅ Critical nature clear

fix-stuff                         # ❌ Too vague
new-feature                       # ❌ Doesn't describe what
john-dev                          # ❌ Person name, not purpose
```

### **Commit Messages:**
```bash
# ✅ Good commit messages:
"Add device auto-reconnection with exponential backoff"
"Fix Windows path separator handling in build scripts"  
"Update PyQt6 table sorting to use QTableWidgetItem"

# ❌ Poor commit messages:
"fix stuff"
"updates"
"working on feature"
```

### **Pull Request Guidelines:**
- **Title**: Clear, concise description of changes
- **Description**: Explain what, why, and how
- **Testing**: Describe how you tested the changes
- **Screenshots**: For UI changes, include before/after images

## 🛠️ **Local Development Setup**

### **Quick Start:**
```bash
# Clone and setup
git clone https://github.com/cyphercolt/usbip-gui-app.git
cd usbip-gui-app
git checkout develop

# Setup environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Test the app
./scripts/launch.sh

# Build executable  
./scripts/build-linux.sh
```

### **Before Submitting PRs:**
```bash
# Format code
source venv/bin/activate
black src/
flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics

# Test build
./scripts/build-linux.sh

# Run basic functionality test
./build-configs/dist/USB-IP-GUI
```

## 🚨 **Emergency Hotfixes**

For critical production issues:

```bash
# Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# Make minimal fix
# Test thoroughly
git commit -m "Fix critical security vulnerability in SSH handling"

# PR directly to main (skip develop)
# After merge, also merge hotfix to develop
```

## 📈 **Release Versioning**

We use **Semantic Versioning** (SemVer):

- **v1.0.0** → **v1.0.1**: Patch (bug fixes)
- **v1.0.0** → **v1.1.0**: Minor (new features, backward compatible)  
- **v1.0.0** → **v2.0.0**: Major (breaking changes)

### **Examples:**
- `v1.2.3`: Version 1, feature set 2, patch 3
- `v2.0.0`: Major rewrite with breaking changes
- `v1.5.1`: Feature release 5 with bug fix 1

## 🎯 **Quick Reference**

| Task | Command |
|------|---------|
| Start new feature | `git checkout develop && git pull && git checkout -b feature/name` |
| Work on existing feature | `git checkout feature/name && git pull origin feature/name` |
| Update from develop | `git checkout develop && git pull && git checkout feature/name && git merge develop` |
| Push feature | `git push -u origin feature/name` |
| Clean up merged branch | `git branch -d feature/name && git push origin --delete feature/name` |
| Emergency hotfix | `git checkout main && git checkout -b hotfix/name` |
| Release to main | Create PR: `develop` → `main` |
| Tag release | `git tag -a v1.0.0 -m "Release v1.0.0" && git push origin v1.0.0` |

---

## 💡 **Tips for New Git Users**

1. **Always pull before starting new work**: `git pull origin develop`
2. **Commit often**: Small, focused commits are easier to review
3. **Use meaningful branch names**: Others should understand what you're working on
4. **Test before pushing**: Make sure your code works locally
5. **Write good commit messages**: Future you will thank you
6. **Don't work directly on main**: Always use feature branches
7. **Keep branches focused**: One feature/fix per branch
8. **Clean up merged branches**: Delete them after PR merge

Remember: **It's better to ask questions than to guess!** 🤝
