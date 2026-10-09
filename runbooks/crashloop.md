# CrashLoopBackOff investigation

## Signals and interpretation
CrashLoopBackOff is a restart-backoff condition, not a root cause. Possible causes include application exit, memory limits, probe failures, and incorrect configuration.

## Investigation
Inspect the last termination reason and exit code, previous logs, restart timestamps, and events. Do not conclude OOMKilled from exit code 137 alone. Compare the evidence to a more specific runbook.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous --tail=100
```

## Review before remediation
Choose a remediation only after identifying a supported cause. A restart may temporarily hide the symptoms.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
