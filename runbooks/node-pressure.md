# Node pressure and evicted pods

## Signals and interpretation
Evicted pods with a specific MemoryPressure or DiskPressure message can indicate node resource pressure. Container OOMKilled and pod eviction are different mechanisms.

## Investigation
Inspect pod eviction events, node conditions, and capacity. Distinguish node-wide pressure from a single container limit. DiskPressure can involve node filesystem or image filesystem capacity.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl describe node <node>
kubectl get nodes
```

## Review before remediation
Investigate capacity, log growth, and resource requests with the infrastructure owner before changing node settings.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/
