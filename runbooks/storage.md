# Volume mount and attachment failures

## Signals and interpretation
FailedMount or FailedAttachVolume indicates that storage setup failed. A Pending PVC may indicate a provisioning or binding issue. These messages require their detailed event context.

## Investigation
Inspect PVC state, storage class, volume access mode, CSI controller events, and the pod node. A missing Secret used for a mount differs from a CSI or topology failure.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc> -n <namespace>
```

## Review before remediation
Coordinate storage changes with an operator. Do not delete claims or volumes as an initial diagnostic action.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/storage/persistent-volumes/
