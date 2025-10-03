# Trust Anchors Directory

This directory contains trusted Certificate Authority (CA) certificates for C2PA validation.

## Structure

```
trust_anchors/
├── adobe/
│   ├── adobe_root_ca.pem
│   └── adobe_intermediate_ca.pem
├── canon/
│   └── canon_c2pa_ca.pem
├── sony/
│   └── sony_c2pa_ca.pem
└── microsoft/
    └── microsoft_c2pa_ca.pem
```

## Adding Trust Anchors

1. Obtain CA certificates from C2PA participants
2. Verify certificate authenticity
3. Convert to PEM format if needed:
   ```bash
   openssl x509 -inform DER -in cert.der -out cert.pem
   ```
4. Place in appropriate subdirectory

## C2PA Trust Model

C2PA uses a hierarchical trust model:
- **Root CA**: Top-level trusted authority
- **Intermediate CA**: Issued by root CA
- **End-entity**: Actual signing certificate

## Verification

Verify certificate validity:
```bash
openssl x509 -in cert.pem -text -noout
```

Check expiration:
```bash
openssl x509 -in cert.pem -enddate -noout
```

## Certificate Rotation

- Monitor certificate expiration dates
- Update certificates before expiry
- Maintain both old and new certificates during transition period

## Sources

Official C2PA trust anchors:
- https://c2pa.org/specifications/specifications/1.0/specs/C2PA_Specification.html#_trust_model
- Content Authenticity Initiative (CAI): https://contentauthenticity.org/

## Security

- Protect private keys (not stored here)
- Regularly audit trust anchor list
- Remove compromised certificates immediately
