# Image pull and registry failures

## Signals and interpretation
ImagePullBackOff and ErrImagePull indicate failure to retrieve an image. A manifest unknown message suggests an incorrect or absent tag. Unauthorized, pull access denied, and registry authentication errors suggest access problems.

## Investigation
Read the full image-pull event, not just the pod status. Compare the image registry, repository, and tag to the intended artifact. Check imagePullSecrets references and namespace. DNS failures and TLS problems require separate investigation.

Read-only checks (replace placeholders):
```sh
kubectl describe pod <pod> -n <namespace>
kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.imagePullSecrets[*].name}'
```

## Review before remediation
Correct the image reference or registry authorization only after verification. Never include secret data in diagnostic reports.

## Reference
Maintainer-authored summary; consult the Kubernetes documentation for cluster-specific details.
https://kubernetes.io/docs/concepts/containers/images/
