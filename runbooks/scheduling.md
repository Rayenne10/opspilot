# Pending pods and resource scheduling

## Signals and interpretation
FailedScheduling with Insufficient cpu or Insufficient memory indicates that pod requests cannot fit available eligible nodes. Pending alone is not enough to diagnose this.

## Investigation
Inspect requests, allocatable resources, node selectors, affinity, and taints. Scheduler decisions use resource requests, not only measured usage. Distinguish insufficient capacity from node eligibility restrictions.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl get nodes
kubectl describe node <node>
```

## Review before remediation
An operator can adjust requests or capacity after reviewing constraints and workload requirements.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/
