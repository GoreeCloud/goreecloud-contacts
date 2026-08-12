# Security

## Purpose

I use this document to define the initial security requirements for GoreeCloud Contacts.

## Credential Handling

I will not store active passwords, CardDAV credentials, private keys, tokens, recovery information, or session secrets in source control.

The repository contains placeholders and non-secret references only. Runtime secrets must be supplied through an approved protected mechanism outside the repository.

## Authentication

The initial architecture may validate an individual user's approved CardDAV credentials against Radicale and then establish an application session. Plaintext passwords must not be written to application logs or persisted in ordinary application storage.

## Authorization

Authentication does not grant unrestricted access. Every request must operate within the authenticated user's authorized CardDAV collections.

## Network Exposure

The production application is intended to use the approved GoreeCloud private-service publication model. Backend application ports must not be exposed directly to the public Internet.

## Logging

Logs must minimize personal contact data. Routine logs should not include full vCards, contact notes, addresses, phone numbers, email addresses, credentials, or session values unless a narrowly scoped troubleshooting need requires temporary protected diagnostic output.

## Development and Testing

Automated tests and local development should use synthetic contact data and non-production credentials. Production contact collections must not be used as a convenient development dataset.

## Security Review Gate

Production deployment requires review of authentication, authorization, session protection, dependency security, CardDAV conflict behavior, logging, container permissions, network exposure, backup, restoration, and rollback.
