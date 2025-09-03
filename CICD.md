# CI/CD Setup for USB/IP GUI App

This repository includes automated GitHub Actions workflows for building and releasing the USB/IP GUI App on both Windows and Linux platforms.

## Workflows

### 1. Build and Release (`build-release.yml`)
**Triggers:** 
- When you create a new tag (e.g., `v1.0.0`)
- When you publish a GitHub release

**Actions:**
- ✅ Builds Windows executable using PyInstaller
- ✅ Builds Linux executable using PyInstaller  
- ✅ Creates release packages with documentation
- ✅ Automatically publishes GitHub release with binaries

### 2. Test Build (`test-build.yml`)
**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`

**Actions:**
- ✅ Tests Windows build process
- ✅ Tests Linux build process
- ✅ Runs code quality checks (flake8, black)
- ✅ Verifies executables are created successfully

### 3. Manual Build (`manual-build.yml`)
**Triggers:**
- Manual dispatch from GitHub Actions tab

**Actions:**
- ✅ Allows selective building (Windows/Linux/Both)
- ✅ Creates artifacts for testing
- ✅ Useful for debugging build issues

## How to Create a Release

### Method 1: Create Tag (Recommended)
```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

### Method 2: GitHub Web Interface
1. Go to your repository on GitHub
2. Click "Releases" → "Create a new release"
3. Choose "Create new tag" and enter version (e.g., `v1.0.0`)
4. Add release title and description
5. Click "Publish release"

### Method 3: Command Line with gh CLI
```bash
# Create release with gh CLI
gh release create v1.0.0 --title "USB/IP GUI App v1.0.0" --notes "Release notes here"
```

## What Happens Automatically

1. **Build Process:**
   - Creates Python virtual environment
   - Installs dependencies
   - Runs PyInstaller to create executables
   - Packages with documentation

2. **Windows Build:**
   - Creates `USB-IP-GUI.exe` 
   - Packages as `USB-IP-GUI-Windows.zip`
   - Includes installation instructions

3. **Linux Build:**
   - Creates `USB-IP-GUI` executable
   - Packages as `USB-IP-GUI-Linux.tar.gz`
   - Includes launcher script and documentation

4. **Release Creation:**
   - Automatically creates GitHub release
   - Uploads both platform packages
   - Includes formatted release notes

## Monitoring Builds

- **View Progress:** Go to "Actions" tab in your GitHub repository
- **Download Artifacts:** Test builds create downloadable artifacts
- **Check Logs:** Click on any workflow run to see detailed logs

## Build Requirements

The workflows automatically handle:
- ✅ Python 3.12 setup
- ✅ Virtual environment creation
- ✅ Dependency installation
- ✅ PyInstaller execution
- ✅ Package creation

## Troubleshooting

### Build Failures
1. Check the Actions logs for detailed error messages
2. Ensure all dependencies are in `requirements.txt`
3. Verify `.spec` files are properly configured

### Missing Artifacts
- Check if the workflow completed successfully
- Artifacts are only created for successful builds
- Manual build artifacts expire after 7 days

### Release Issues
- Ensure you have proper repository permissions
- Tags must start with `v` (e.g., `v1.0.0`, `v2.1.3`)
- Release creation requires push access to the repository

## File Structure

```
.github/
└── workflows/
    ├── build-release.yml    # Automated releases
    ├── test-build.yml       # Testing on push/PR
    └── manual-build.yml     # Manual testing builds
```

## Customization

To modify the build process:
1. Edit the appropriate `.yml` file in `.github/workflows/`
2. Commit and push changes
3. The next workflow run will use the updated configuration

The workflows are designed to be reliable and require no manual intervention for regular releases.
