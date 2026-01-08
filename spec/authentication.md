# Authentication Specification

## Overview

This specification defines the authentication system for k8s-cli. The system provides a simple username-based authentication mechanism for both CLI and REST API interfaces, enabling user isolation and resource tracking.

## Requirements

### Core Functionality

#### User Login
- The system MUST allow users to log in with a username via the CLI
- The system MUST store the current user's credentials locally for subsequent commands
- The system SHOULD provide feedback when login is successful
- The system MAY support displaying the current logged-in user

#### User Identification
- The system MUST provide a mechanism to retrieve the current user for CLI commands
- The system MUST require an `X-User` header for all REST API requests
- The system MUST use the username for resource isolation and authorization

#### User Session Storage
- The system MUST store the logged-in username in a local configuration file
- The system MUST read the stored username for CLI commands that require authentication
- The system SHOULD handle cases where no user is logged in

### CLI Interface

- The system MUST provide an `auth login` command to log in as a user
- The system MUST provide an `auth whoami` command to display the current user
- The system SHOULD display the logged-in username after successful login

### REST API Interface

- The system MUST require an `X-User` header on all authenticated endpoints
- The system MUST extract the username from the `X-User` header
- The system MUST use the username for authorization decisions
- The system SHOULD return 4xx errors if the `X-User` header is missing

### User Isolation

- The system MUST use the username to isolate tasks by Kubernetes labels
- The system MUST use the username to isolate volumes by Kubernetes labels
- The system MUST prevent users from accessing resources owned by other users
- The system MAY allow privileged operations to bypass user isolation

### Username Sanitization

- The system MUST sanitize usernames for use in Kubernetes labels
- The system MUST replace `@` characters with `-` in usernames
- The system MUST ensure sanitized usernames comply with DNS-1123 subdomain rules

### Error Handling

- The system MUST provide clear error messages when login fails
- The system MUST handle file system errors when storing user credentials
- The system SHOULD handle missing user sessions gracefully

## Implementation Notes

- User credentials are stored locally in the user's home directory
- The username is passed via the `X-User` header from CLI to API
- Username sanitization ensures compatibility with Kubernetes label requirements
- No password or token validation is performed (trusted environment model)

## Security Considerations

This authentication system is designed for trusted environments (e.g., internal clusters, personal workstations). The following security considerations apply:

- This system does NOT provide password-based authentication
- This system does NOT provide token-based authentication
- This system does NOT provide encryption for stored credentials
- This system relies on the security of the local file system
- This system relies on the security of the API endpoint (network isolation)

For production deployments, consider integrating with:
- OAuth 2.0 / OpenID Connect
- Kubernetes service accounts
- Corporate authentication systems (LDAP, SAML)
- Token-based authentication with revocation
