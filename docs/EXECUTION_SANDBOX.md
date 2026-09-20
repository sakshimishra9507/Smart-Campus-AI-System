# Repository Execution Sandbox

Repository code is executed only inside a Docker container. The host process may invoke Docker, but never invokes repository commands directly.

Isolation:
- repository mounted read-only at /workspace
- container root filesystem read-only
- bounded writable /tmp tmpfs
- network namespace disabled
- all Linux capabilities dropped
- no-new-privileges enabled
- CPU, memory, PID, file-descriptor and wall-clock limits
- minimal environment variables
- no shell execution
- strict command allowlist
- relative targeted-test paths only

Supported operations: run_tests(), run_targeted_tests(path), run_linter(), run_type_checker().

If Docker is unavailable the sandbox fails closed instead of falling back to host execution.

Build docker/sandbox.Dockerfile as repository-sandbox:latest. For production, pin the image by immutable digest.
