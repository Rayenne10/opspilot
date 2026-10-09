# Container memory exhaustion

## Signals and interpretation
OOMKilled, a terminated container, and growing restart counts support investigating a container memory limit. Exit code 137 alone does not prove an out-of-memory kill.

## Investigation
Check the termination reason in pod describe output. Compare resource requests and limits with workload demand. Metrics describe present usage and may miss a past spike. Examine previous logs and timestamps. Distinguish a container limit from node-wide memory pressure.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous --tail=100
kubectl top pod <pod> -n <namespace>
```

## Review before remediation
Tune limits only after understanding the workload and available capacity. A leak requires application investigation.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/
