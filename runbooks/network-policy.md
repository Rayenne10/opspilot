# Network policy investigation

## Signals and interpretation
Connection timeouts may be consistent with blocked traffic, unreachable addresses, or an overloaded target. A timeout alone does not establish NetworkPolicy as the cause.

## Investigation
Inspect ingress and egress policies, namespace selectors, pod labels, service endpoints, and DNS reachability. Verify that the cluster network plugin implements NetworkPolicy.

Read-only checks (replace placeholders):
```sh
kubectl get networkpolicies -n <namespace>
kubectl describe networkpolicy <policy> -n <namespace>
kubectl get endpointslices -n <namespace>
```

## Review before remediation
Request a reviewed least-privilege policy change after verifying intended traffic.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/services-networking/network-policies/
