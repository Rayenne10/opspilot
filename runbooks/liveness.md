# Liveness probes and restarts

## Signals and interpretation
Liveness probe failed can trigger container restarts after the failure threshold is reached. A slow start may require a startup probe; a readiness failure alone is different.

## Investigation
Align restart timestamps with failed liveness events. Read previous logs. Check probe path and port, startup time, timeout, and failure threshold. Avoid treating a dependency outage as proof that restarting the application will help.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous --tail=100
```

## Review before remediation
Correct the application fault or review probe semantics and timing. Do not disable probes blindly.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/workloads/pods/probes/
