# AD Role Mapping Tool - Deployment Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Deployment Options](#deployment-options)
3. [Security Considerations](#security-considerations)
4. [Installation Process](#installation-process)
5. [Configuration Management](#configuration-management)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Backup and Recovery](#backup-and-recovery)
8. [Maintenance Procedures](#maintenance-procedures)
9. [Scaling Considerations](#scaling-considerations)
10. [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware Requirements
- CPU: 2+ cores recommended
- RAM: Minimum 4GB (8GB+ recommended for large datasets)
- Storage: 1GB for installation + space for input/output files
- Network: Internet access for initial setup (pip packages)

### Software Requirements
- Operating System:
  - Linux (Ubuntu 20.04+, CentOS 7+)
  - macOS 10.15+
  - Windows 10/11 with WSL2
- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, for version control)
- Virtual environment support (venv)

### Dependencies
- pandas>=2.0.0
- openpyxl>=3.1.0
- python-dotenv>=1.0.0
- pytest>=7.0.0 (for testing)

### File System
- Read/write permissions for:
  - Application directory
  - Input directory
  - Output directory
  - Log directory

## Deployment Options

### 1. Local Installation
Best for individual users or small teams:
```bash
git clone [repository-url]
cd build_AD_roles
./init.sh
```

### 2. Shared Server Installation
For team environments:
1. Create dedicated service account
2. Set up shared directories:
   ```bash
   sudo mkdir -p /opt/ad_role_mapper
   sudo mkdir -p /var/log/ad_role_mapper
   sudo mkdir -p /etc/ad_role_mapper
   sudo chown -R service_account:service_group /opt/ad_role_mapper
   ```

3. Deploy application:
   ```bash
   cd /opt/ad_role_mapper
   git clone [repository-url] .
   ./init.sh
   ```

### 3. Docker Deployment
For containerized environments:

1. Create Dockerfile:
```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

VOLUME ["/app/input", "/app/output"]
ENTRYPOINT ["python", "src/AD_oracle.py"]
```

2. Build and run:
```bash
docker build -t ad_role_mapper .
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output ad_role_mapper
```

## Security Considerations

### File Permissions
1. Set restrictive permissions:
   ```bash
   chmod 750 /opt/ad_role_mapper
   chmod 640 .env
   chmod 640 src/builtin_groups.json
   ```

2. Use appropriate ownership:
   ```bash
   chown -R service_account:service_group /opt/ad_role_mapper
   ```

### Environment Variables
1. Restrict .env access:
   ```bash
   chmod 600 .env
   ```

2. Use secure paths:
   ```ini
   INPUT_DIR=/secure/input
   OUTPUT_DIR=/secure/output
   LOG_DIR=/var/log/ad_role_mapper
   ```

### Input Validation
1. Validate file permissions
2. Check file ownership
3. Verify file extensions
4. Validate data formats

### Audit Logging
Enable comprehensive logging:
```ini
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Installation Process

### 1. Pre-installation Tasks
1. Verify system requirements
2. Create service account
3. Set up directories
4. Configure permissions

### 2. Application Installation
1. Clone repository:
   ```bash
   git clone [repository-url] /opt/ad_role_mapper
   cd /opt/ad_role_mapper
   ```

2. Set up environment:
   ```bash
   ./init.sh
   ```

3. Configure application:
   ```bash
   cp .env.example .env
   vim .env  # Set environment-specific values
   ```

### 3. Post-installation Tasks
1. Verify permissions
2. Test configuration
3. Run validation tests
4. Document installation

## Configuration Management

### Configuration Files
1. Environment Variables (.env):
   ```ini
   LOG_LEVEL=INFO
   EXCEL_MAX_ROWS=1000000
   EXCEL_MAX_COLS=16384
   ```

2. Builtin Groups (builtin_groups.json):
   ```json
   {
     "Original_Role_Groups": [],
     "Additional_Role_Groups": []
   }
   ```

### Version Control
1. Track configurations:
   ```bash
   git init /etc/ad_role_mapper
   git config --global user.name "Admin"
   git config --global user.email "admin@example.com"
   ```

2. Commit changes:
   ```bash
   git add .
   git commit -m "Update configuration"
   ```

## Monitoring and Logging

### Log Configuration
1. Set up log rotation:
   ```bash
   sudo vim /etc/logrotate.d/ad_role_mapper
   ```
   ```
   /var/log/ad_role_mapper/*.log {
       daily
       rotate 14
       compress
       delaycompress
       missingok
       notifempty
       create 0640 service_account service_group
   }
   ```

### Monitoring
1. Check application status:
   ```bash
   tail -f /var/log/ad_role_mapper/app.log
   ```

2. Monitor resource usage:
   ```bash
   top -u service_account
   df -h /opt/ad_role_mapper
   ```

## Backup and Recovery

### Backup Procedures
1. Configuration backup:
   ```bash
   tar czf config_backup.tar.gz .env builtin_groups.json
   ```

2. Data backup:
   ```bash
   rsync -av input/ backup/input/
   rsync -av output/ backup/output/
   ```

### Recovery Procedures
1. Restore configuration:
   ```bash
   tar xzf config_backup.tar.gz
   ```

2. Restore data:
   ```bash
   rsync -av backup/input/ input/
   rsync -av backup/output/ output/
   ```

## Maintenance Procedures

### Regular Maintenance
1. Update dependencies:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. Clean old files:
   ```bash
   find output/ -type f -mtime +30 -delete
   ```

3. Check logs:
   ```bash
   journalctl -u ad_role_mapper
   ```

### Performance Optimization
1. Monitor memory usage
2. Clean temporary files
3. Optimize input data
4. Update indexes

## Scaling Considerations

### Vertical Scaling
1. Increase resources:
   - Add more RAM
   - Upgrade CPU
   - Expand disk space

### Horizontal Scaling
1. Load distribution:
   - Process different datasets on separate instances
   - Share configuration across instances
   - Centralize logging

### Performance Tuning
1. Memory optimization:
   ```ini
   CHUNK_SIZE=10000
   MAX_WORKERS=4
   ```

2. Disk I/O optimization:
   - Use SSD storage
   - Implement proper indexing
   - Optimize file access patterns

## Troubleshooting

### Common Issues

1. Permission Errors
   ```
   Error: Permission denied
   Solution: Check file/directory permissions and ownership
   ```

2. Resource Issues
   ```
   Error: MemoryError
   Solution: Increase available RAM or reduce chunk size
   ```

3. Configuration Issues
   ```
   Error: Configuration file not found
   Solution: Verify file paths and permissions
   ```

### Debug Procedures
1. Enable debug logging:
   ```bash
   LOG_LEVEL=DEBUG
   ```

2. Check system resources:
   ```bash
   top
   df -h
   ```

3. Verify permissions:
   ```bash
   ls -la /opt/ad_role_mapper
   ```

### Support Process
1. Check documentation
2. Review log files
3. Contact support team
4. Provide:
   - Error messages
   - Log files
   - Configuration files
   - System information
