# Service connections and EndpointSlices

## Signals and interpretation
connection refused suggests an address was reached but the target port did not accept the connection, or an intermediate rejection occurred. It does not by itself prove a NetworkPolicy issue.

## Investigation
Inspect service port and targetPort, label selectors, ready EndpointSlice addresses, and application listening ports. A timeout has several possible causes and needs separate evidence.

Read-only checks (replace placeholders):
```sh
kubectl get services -n <namespace>
kubectl get endpointslices -n <namespace>
kubectl describe service <service> -n <namespace>
```

## Review before remediation
Apply a reviewed correction to selectors, ports, or application binding after confirming the mismatch.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/
