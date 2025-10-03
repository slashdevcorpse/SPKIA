# SPKIA Privacy Policy

**Last Updated: October 2, 2025**

## Overview

SPKIA (Sensor-PKI Authenticity) is committed to protecting your privacy. This policy explains how we handle data during media verification.

## Data Collection

### What We Collect
- **Media files** (images/videos) - Temporarily processed for verification
- **File metadata** (EXIF, XMP) - Extracted for analysis
- **Verification results** - Classification labels and confidence scores
- **Job metadata** - File hash, size, timestamps

### What We DON'T Collect
- ❌ User accounts or profiles
- ❌ Personal information
- ❌ IP addresses or tracking data
- ❌ Permanent copies of your media
- ❌ Browsing history

## Data Processing

### Verification Process
1. You upload a file or provide a URL
2. File is temporarily stored in memory/disk
3. Cryptographic and ML analysis performed
4. Results generated and returned
5. **All data automatically deleted within 24 hours**

### Processing Location
- All processing occurs on our servers
- No third-party services access your media
- No cloud storage services used

## Data Retention

### Automatic Deletion
- **Uploaded files**: Deleted immediately after processing
- **Job data**: Deleted after 24 hours (TTL)
- **Verification results**: Deleted after 24 hours
- **Temporary files**: Deleted within minutes

### Manual Deletion
You can force immediate deletion of your data:
- Click "Delete Data Now" button in the UI
- API: `DELETE /api/verify/{job_id}`

## Data Security

### Protection Measures
- ✅ TLS encryption in transit
- ✅ Ephemeral processing (no persistent storage)
- ✅ Isolated job processing
- ✅ No cross-user data access
- ✅ Regular security audits

### What We Log
- **Aggregate metrics** (anonymized):
  - Total verifications count
  - % authentic vs AI-generated
  - Average processing time
- **NO individual file content or results**

## Analytics

### Metrics Collection
We collect anonymized aggregate statistics:
- Total verification requests
- Authentication method distribution (C2PA, Sensor-PKI, ML)
- System performance metrics

These metrics contain **NO personally identifiable information**.

## Third-Party Services

SPKIA is **fully self-hosted** and does not:
- Share data with third parties
- Use external analytics services
- Send data to advertisers
- Employ tracking pixels or cookies

## Your Rights

### You Have the Right To:
- ✅ Delete your verification data immediately
- ✅ Know exactly what data we process
- ✅ Use the service anonymously
- ✅ Export your verification results (while available)

### How to Exercise Your Rights:
- **Delete data**: Use the "Delete Now" button or API endpoint
- **Questions**: Contact privacy@spkia.org
- **Concerns**: File issue on GitHub

## Open Source Transparency

SPKIA is **open source**:
- All code is public on GitHub
- You can audit our data handling
- Self-hosting option available
- Community-driven development

## Children's Privacy

SPKIA does not knowingly collect data from children under 13. No age verification is required because we collect no personal information.

## Changes to This Policy

We will notify users of policy changes via:
- GitHub repository announcements
- Version updates in the application
- Privacy policy version number

## Contact Us

**Privacy Questions:**
- Email: privacy@spkia.org
- GitHub Issues: https://github.com/your-org/spkia/issues

**Security Issues:**
- Email: security@spkia.org
- PGP Key: [Link to public key]

## Legal Compliance

SPKIA complies with:
- GDPR (European Union)
- CCPA (California)
- Privacy-by-design principles

## Summary

🔒 **We don't store your media permanently**  
⏰ **Everything deleted within 24 hours**  
🚫 **No tracking, no ads, no third parties**  
✅ **You can delete data immediately**  
📖 **Fully transparent and open source**

---

**SPKIA v1.0 | Open Source Privacy-First Verification**
