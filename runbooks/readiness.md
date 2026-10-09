# Readiness probe failures

## Signals and interpretation
Readiness probe failed indicates that a pod is not ready for service traffic. A failed readiness probe does not itself restart the container. HTTP 503 may indicate an unavailable application or dependency.

## Investigation
Compare the configured HTTP path, port, protocol, initial delay, and timeout with application behavior. Inspect EndpointSlices and application logs. Do not assume all health failures have the same root cause.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl get endpointslices -n <namespace>
kubectl logs <pod> -n <namespace> --tail=100
```

## Review before remediation
Restore application readiness or correct probe configuration through a reviewed change.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/workloads/pods/probes/
