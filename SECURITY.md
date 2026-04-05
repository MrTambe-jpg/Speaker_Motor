# Security Policy

## Supported Versions

We support the following versions of OMNISOUND with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| 0.2.x   | :x:                |
| 0.1.x   | :x:                |

## Reporting a Vulnerability

We use **GitHub Security Advisories** for private vulnerability reporting.

- **Report via**: [GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
- **Email**: conduct@omnisound-project.org (for non-Github reports)

**Please include:**
1. Description of the vulnerability
2. Steps to reproduce the issue
3. Potential impact of the vulnerability
4. Any known fixes or workarounds

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Timeline**: Within 14 days for critical issues
- **Public Disclosure**: Coordinated with reporter

## Security Considerations

### WiFi Network Security

The ESP32 creates a WiFi access point. Consider the following:

- **Default SSID**: "OMNISOUND" (changeable in code)
- **Default Password**: "12345678" (**CHANGE BEFORE DEPLOYMENT**)
- **Network Isolation**: This AP should NOT be used for sensitive operations

### Recommendations

1. **Change Default Password**: Edit `main.cpp` before deployment:
   ```cpp
   const char* apPass = "your-secure-password";
   ```

2. **Use for Local Networks Only**: This system is designed for local/offline use

3. **No Sensitive Data**: Don't transmit sensitive data over WebSocket

4. **Firmware Updates**: Keep firmware updated for security patches

## Known Security Limitations

- **No Encryption**: WebSocket traffic is not encrypted (expected for local AP)
- **No Authentication**: No user authentication on the web interface
- **Open WiFi**: The ESP32 AP uses WPA2 (not open, but password is weak by default)

These limitations are by design — this is a local, offline system.

## Third-Party Dependencies

| Dependency | Version | Vulnerability Check |
|------------|---------|---------------------|
| ESP32 Arduino | Latest | [Link](https://github.com/espressif/arduino-esp32/security) |
| WebSockets | ^2.4.1 | [Link](https://github.com/Links2004/arduinoWebSockets/security) |
| FastAPI | >=0.109.0 | [Link](https://github.com/fastapi/fastapi/security) |
| React | ^18.2.0 | [Link](https://github.com/facebook/react/security) |
| Zustand | ^4.4.7 | [Link](https://github.com/pmndrs/zustand/security) |
| numpy | >=1.24.0 | [Link](https://github.com/numpy/numpy/security) |

## Best Practices

### For Production Deployment

1. **Network Isolation**: Run on isolated network/VLAN
2. **Firewall**: Block unnecessary ports
3. **Monitor**: Watch for unusual WebSocket traffic
4. **Updates**: Keep all dependencies updated
5. **Change Default Credentials**: WiFi password, any default configs

### For Development

1. **Don't Commit Secrets**: Never commit WiFi passwords or API keys
2. **Use .env**: Store sensitive config in environment variables
3. **Code Review**: Review all changes before merging
4. **Dependabot**: Keep dependencies updated via automated PRs

## Security Hall of Fame

Thank you to everyone who has responsibly disclosed security issues:

| Reporter | Issue | Date |
|----------|-------|------|
| *(Your name here)* | *(First responsible disclosure)* | — |

---

*Thank you for helping keep OMNISOUND secure!*