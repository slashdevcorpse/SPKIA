# Contributing to SPKIA

Thank you for your interest in contributing to SPKIA! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug is already reported in GitHub Issues
2. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, browser, etc.)
   - Logs or error messages

### Suggesting Features

1. Check existing feature requests
2. Create an issue with:
   - Clear use case description
   - Proposed solution
   - Alternatives considered
   - Impact on privacy/security

### Submitting Code

#### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/spkia.git
cd spkia

# Copy environment file
cp .env.example .env

# Start development environment
docker-compose up -d
```

#### Code Style

**Python (Backend)**:
- Follow PEP 8
- Use Black for formatting: `black app/`
- Use type hints
- Write docstrings for public functions

**TypeScript (Frontend)**:
- Follow project ESLint rules
- Use Prettier for formatting
- Write JSDoc comments for complex functions

#### Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow code style guidelines
   - Write/update tests
   - Update documentation

3. **Test your changes**
   ```bash
   # Backend tests
   cd backend
   pytest tests/ --cov=app

   # Frontend tests
   cd frontend
   npm test
   ```

4. **Commit with descriptive messages**
   ```bash
   git commit -m "Add: Feature description"
   ```

   Commit message prefixes:
   - `Add:` New feature
   - `Fix:` Bug fix
   - `Update:` Changes to existing feature
   - `Docs:` Documentation changes
   - `Refactor:` Code refactoring
   - `Test:` Test additions/changes

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a Pull Request on GitHub with:
   - Clear title and description
   - Reference related issues
   - Screenshots (if UI changes)

6. **Code Review**
   - Address review comments
   - Update PR as needed
   - Maintain clean commit history

#### Testing Requirements

All PRs must include:
- ✅ Unit tests for new functions
- ✅ Integration tests for API endpoints
- ✅ Updated documentation
- ✅ Passing CI/CD checks

### ML Model Contributions

#### Training New Models

1. Document training dataset and methodology
2. Provide model performance metrics
3. Include model versioning
4. Update `models/README.md`

#### Model Requirements

- **Precision** > 92%
- **Recall** > 90%
- **F1-Score** > 91%
- **Model size** < 200MB (for deployment)

### Documentation

- Update README.md for feature changes
- Add API documentation for new endpoints
- Update architecture diagrams if needed
- Write clear inline comments

## Development Guidelines

### File Organization

Follow the project structure:
```
backend/
├── app/
│   ├── api/          # API routes
│   ├── models/       # Data models
│   ├── services/     # Business logic
│   └── utils/        # Utilities
frontend/
├── src/
│   ├── components/   # Reusable components
│   ├── pages/        # Page components
│   ├── services/     # API clients
│   └── types/        # TypeScript types
```

### Code Quality

- **Single Responsibility**: Each function/class does one thing
- **File Length**: Max 500 lines per file
- **Function Length**: Max 50 lines per function
- **Naming**: Clear, descriptive names
- **Comments**: Explain "why", not "what"

### Security Best Practices

- Never commit secrets or API keys
- Validate all user inputs
- Use parameterized queries
- Follow OWASP guidelines
- Report security issues privately to security@spkia.org

## Project Priorities

1. **Privacy**: No permanent data storage
2. **Security**: Cryptographic integrity
3. **Accuracy**: High detection precision
4. **Performance**: < 2s image verification
5. **Usability**: Clear, intuitive UI

## Getting Help

- 💬 **Discussions**: Use GitHub Discussions for questions
- 🐛 **Bugs**: Create GitHub Issues
- 📧 **Email**: dev@spkia.org
- 📖 **Docs**: https://docs.spkia.org

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Acknowledged in documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for making SPKIA better!** 🚀
