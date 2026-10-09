import yaml

from app.config import ROOT


def test_deployment_yaml_and_resource_invariants():
    count = 0
    for file in (ROOT / "deploy").rglob("*.yaml"):
        for document in yaml.safe_load_all(file.read_text()):
            assert isinstance(document, dict), file
            assert "apiVersion" in document and "kind" in document
            if document["kind"] == "Pod":
                assert document["spec"]["automountServiceAccountToken"] is False
                assert document["spec"]["containers"]
            count += 1
    assert count >= 15
    app = next(yaml.safe_load_all((ROOT / "deploy/k8s/base/app.yaml").read_text()))
    container = app["spec"]["template"]["spec"]["containers"][0]
    assert container["securityContext"]["readOnlyRootFilesystem"]
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert container["startupProbe"]["httpGet"]["path"] == "/readyz"


def test_compose_and_ci_config():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    assert compose["services"]["app"]["ports"] == ["127.0.0.1:8000:8000"]
    assert compose["services"]["qdrant"]["profiles"] == ["live"]
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text())
    assert workflow["jobs"]["container"]["needs"] == ["verify", "browser"]
    # A YAML 1.1 parser interprets the 'on' key as True; GitHub uses its workflow schema.
    assert "on" in workflow or True in workflow
    assert not (ROOT / ".env").exists()
