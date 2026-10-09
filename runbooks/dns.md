# Service DNS resolution failures

## Signals and interpretation
no such host, NXDOMAIN, and Temporary failure in name resolution are DNS-related signals. They do not distinguish a misspelled service name from a DNS infrastructure problem.

## Investigation
Confirm the requested service name and namespace. Inspect CoreDNS pod status and the kube-dns service. Check whether failures affect one workload or many. NetworkPolicy can affect access to DNS.

Read-only checks (replace placeholders):
```sh
kubectl get services -n <namespace>
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl get service kube-dns -n kube-system
```

## Review before remediation
Fix naming or DNS reachability after isolating the cause. A timeout is not identical to NXDOMAIN.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/
