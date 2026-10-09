# Running OpsPilot on Kubernetes

Use a disposable local Kind or k3s cluster first. Commands below assume Docker and kubectl are installed. The application does not collect cluster evidence automatically.

## Local Kind demo

```sh
kind create cluster --name opspilot
docker build -t opspilot:local .
kind load docker-image opspilot:local --name opspilot
kubectl apply -k deploy/k8s/base
kubectl rollout status deployment/opspilot -n opspilot --timeout=180s
kubectl port-forward service/opspilot -n opspilot 8000:8000
```

Open http://localhost:8000. For k3s, import the built image into its container runtime or change the manifest image to an accessible registry reference. After GitHub CI publishes a GHCR image, use its immutable SHA tag. A private GHCR package requires an imagePullSecret; do not assume a package is publicly pullable.

## Live overlay

Before applying the overlay, create a Secret with keys `openai-api-key` and optionally `api-token` in namespace `opspilot`. Supply the values from local files or your existing secrets workflow; never commit them to manifests. For example, with protected local files:

```sh
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create secret generic opspilot-secrets -n opspilot \
  --from-file=openai-api-key=/path/to/openai-key \
  --from-file=api-token=/path/to/workspace-token
kubectl apply -k deploy/k8s/live
kubectl rollout status deployment/opspilot -n opspilot --timeout=300s
```

Secret files must contain only the key/token with no trailing newline. The Qdrant PVC needs a working default storage class. Kind does not necessarily include a dynamic storage provisioner; configure one or adapt the volume to a local disposable storage setup. k3s commonly provides a local-path provisioner. The Qdrant NetworkPolicy requires a policy-capable CNI to enforce restrictions.

The app stays at one replica for this small deployment. Simultaneous initializers on a new collection are not coordinated across processes; do not scale it without adding shared ingestion coordination. Startup readiness includes indexing; ongoing vector/provider failures are reported on investigation requests rather than changing readiness.

## Incident lab

```sh
kubectl apply -k deploy/lab
kubectl get pods -n opspilot-lab
```

| Pod | Intentional behavior |
| --- | --- |
| `memory-failure` | Allocates above its container memory limit |
| `missing-image` | Uses an absent image tag |
| `missing-config` | References a missing Secret |
| `readiness-failure` | Always returns HTTP 503 to the readiness probe |

Wait for image pulls, events, and restarts before collecting evidence. Failures can depend on cluster/runtime behavior; inspect actual events rather than assuming the expected result.

```sh
python scripts/collect_incident.py memory-failure -n opspilot-lab
# Submit reviewed incident.json using curl or paste its fields into the UI:
curl -s http://localhost:8000/api/analyze \
  -H 'Content-Type: application/json' --data-binary @incident.json
```

Use `--container` for multi-container pods. Optional namespace-scoped RBAC for a separate collector is in `deploy/collector-rbac.yaml`; the web app never receives that service account. Collection can include sensitive configuration visible in describe output, so review the file.

Clean up the disposable lab when finished:

```sh
kubectl delete namespace opspilot-lab
kind delete cluster --name opspilot
```

## Troubleshooting

- **Live startup fails:** check mode, local API key configuration, provider access, and Qdrant availability. Restart after fixing configuration.
- **502 during analysis:** provider refused/timed out, output was incomplete, or validation rejected unsupported evidence/citations/commands. Inspect sanitized application logs and provider settings.
- **503 busy:** active investigations reached the configured concurrency limit. Retry; requests are not put in an unbounded queue.
- **No cause offered:** more evidence is required. Provide previous logs, termination state, and relevant events.
- **Container or PVC Pending:** inspect image access, scheduling events, and storage provisioner configuration.
- **PowerShell curl behavior:** use `curl.exe` rather than the PowerShell alias when following curl commands.
