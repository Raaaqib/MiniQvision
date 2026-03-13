# Contributing to Raaqib NVR

Thank you for your interest in contributing to Raaqib! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Documentation](#documentation)

---

## Code of Conduct

- Be respectful and inclusive
- Welcome all types of contributions
- Provide constructive feedback
- Focus on the code, not the coder

---

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature/fix
4. Make your changes
5. Submit a pull request

---

## Development Setup

### Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/raaqib-nvr.git
cd raaqib-nvr/Raaqib-Docker
```

### Create Development Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### Install Development Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\Activate.ps1  # Windows

# Install with dev dependencies
pip install -r requirements.txt
pip install -e .  # Install in editable mode

# Install linting tools
pip install black pylint flake8 pytest
```

---

## Making Changes

### Code Areas

| Area | Files | Purpose |
|------|-------|---------|
| Capture | `camera/capture.py` | Frame capture from streams |
| Motion | `motion/motion.py` | Background subtraction |
| Detection | `detectors/pool.py` | YOLO inference workers |
| Tracking | `object_processing.py` | Object ID persistence |
| Recording | `record/recording.py` | FFmpeg clip writing |
| API | `api/app.py` | REST endpoints |
| Database | `database.py` | Event storage |
| MQTT | `mqtt.py` | Event publishing |

### Important Notes

1. **Preserve Process Isolation**: Changes should not break multiprocessing architecture
2. **Test with Real Cameras**: Use actual RTSP streams when possible
3. **Check Thread Safety**: IPC queues must remain thread-safe
4. **Document Changes**: Update relevant markdown files
5. **Backward Compatibility**: Don't break existing config formats

---

## Testing

### Run Unit Tests

```bash
pytest tests/
```

### Manual Testing

1. **Test with USB Webcam**:
   ```bash
   python app.py
   # Press Ctrl+C after 30 seconds
   ```

2. **Verify API**:
   ```bash
   curl http://localhost:8000/api/status | jq .
   ```

3. **Check Logs**:
   ```bash
   tail -100 logs/raaqib.log
   ```

4. **Verify Recordings**:
   ```bash
   ls -la recordings/*/
   ```

---

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints where possible
- Max line length: 100 characters
- 4-space indentation

### Format Code

```bash
# Auto-format with black
black .

# Check style
flake8 .

# Lint with pylint
pylint **/*.py
```

### Example Code

```python
"""
Module description.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CameraCapture:
    """Capture frames from video source."""
    
    def __init__(self, camera_id: str, source: str):
        """Initialize capture process.
        
        Args:
            camera_id: Unique camera identifier
            source: RTSP URL or USB device index
        """
        self.camera_id = camera_id
        self.source = source
    
    def read_frame(self) -> Optional[bytes]:
        """Read next frame.
        
        Returns:
            Frame data or None if unavailable
        """
        # Implementation...
        pass
```

---

## Submitting Changes

### Before Submitting

1. Ensure code follows style guide:
   ```bash
   black . && flake8 .
   ```

2. Run tests:
   ```bash
   pytest tests/
   ```

3. Update documentation if needed

4. Test with real cameras if possible

### Create Pull Request

1. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Go to GitHub and create PR
3. Fill in PR template
4. Wait for review

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Tested with USB camera
- [ ] Tested with RTSP stream
- [ ] API endpoints verified

## Changes Made
- Change 1
- Change 2

## Related Issues
Closes #123
```

---

## Documentation

### Update Documentation When

- Adding new API endpoints
- Changing configuration options
- Modifying installation steps
- Updating troubleshooting

### Doc Files

| File | Purpose |
|------|---------|
| [README.md](README.md) | Overview and quick start |
| [INSTALLATION.md](INSTALLATION.md) | Setup instructions |
| [RUNNING.md](RUNNING.md) | Running and stopping |
| [API.md](API.md) | REST API reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [CONFIGURATION.md](CONFIGURATION.md) | Config options |

### Doc Format

Use Markdown with:
- Clear headers
- Code blocks with language specified
- Examples
- Tables for reference data
- Links to related docs

---

## Common Contribution Areas

### Easy First Issues

- Documentation improvements
- Error message clarity
- Code comments
- Configuration examples

### Moderate Difficulty

- New output formats (HLS, RTMP)
- Additional detection classes
- Performance optimizations
- New camera support

### Complex Issues

- Distributed architecture
- GPU optimization
- Advanced tracking algorithms
- Real-time streaming

---

## Getting Help

- **Questions**: Open a discussion on GitHub
- **Bugs**: Open an issue with minimal reproduction
- **Features**: Discuss before implementing

---

## Release Process

Maintainers will:
1. Review and merge changes
2. Update version number
3. Update CHANGELOG
4. Tag release
5. Publish to PyPI (if applicable)

---

## License

By contributing, you agree your code is licensed under MIT License.

---

Thank you for contributing to Raaqib!
