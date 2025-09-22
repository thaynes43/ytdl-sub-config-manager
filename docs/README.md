# Documentation

This directory contains all documentation for the ytdl-sub Config Manager project.

## Available Documentation

### 📋 [Requirements](requirements.md)
**Purpose**: MVP requirements and technical specifications  
**Audience**: Developers, project managers  
**Contents**:
- Functional requirements
- Non-functional requirements  
- Configuration specifications
- Project structure guidelines
- Implementation requirements
- Testing requirements
- Acceptance criteria

### 🐳 [Docker Usage Guide](docker.md)
**Purpose**: Complete Docker setup and usage instructions  
**Audience**: DevOps, developers, end users  
**Contents**:
- Quick start with Docker Compose
- Direct Docker usage
- Helper scripts documentation
- Environment variables reference
- Volume mounting guide
- GitHub Actions CI/CD
- Troubleshooting guide
- Security considerations

### 🐛 [Debug Guide](debug.md)
**Purpose**: VS Code debugging setup and workflows  
**Audience**: Developers  
**Contents**:
- VS Code debug configurations
- Environment setup (.env files)
- Breakpoint strategies
- Configuration precedence testing
- VS Code tasks and shortcuts
- Troubleshooting debug issues
- Custom debug configuration examples

### 📜 [Legacy Implementation](old-implementation.py)
**Purpose**: Original monolithic implementation for reference  
**Audience**: Developers (for migration reference)  
**Contents**:
- Complete original script
- All classes and functions
- Configuration patterns
- Selenium automation logic
- GitHub integration
- Error handling patterns

## Documentation Standards

### File Naming
- Use lowercase with hyphens: `docker.md`, `debug.md`
- Keep names descriptive but concise
- Avoid abbreviations when possible

### Content Structure
All documentation should follow this structure:
1. **Title and brief description**
2. **Quick Start** section for immediate value
3. **Detailed sections** with clear headings
4. **Examples** with code blocks
5. **Troubleshooting** section when applicable
6. **References** to related documentation

### Markdown Standards
- Use `#` for main title, `##` for sections, `###` for subsections
- Include code blocks with language specification
- Use **bold** for emphasis, *italic* for notes
- Include table of contents for long documents
- Add cross-references between related docs

### Maintenance
- Update documentation when features change
- Verify all links work correctly
- Keep examples current with latest version
- Remove outdated information promptly

## Quick Reference

| Document | Purpose | Last Updated |
|----------|---------|--------------|
| [requirements.md](requirements.md) | Technical specifications | Initial |
| [docker.md](docker.md) | Docker usage guide | v0.1.0 |
| [debug.md](debug.md) | VS Code debugging | v0.1.0 |
| [old-implementation.py](old-implementation.py) | Legacy reference | Archive |

## Contributing to Documentation

When adding new documentation:
1. Create the file in the `docs/` directory
2. Follow the naming conventions above
3. Update this README.md index
4. Update the main project README.md if needed
5. Test all links and examples
6. Consider adding to the main navigation
