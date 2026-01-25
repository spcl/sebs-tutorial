# SeBS Tutorial: Benchmarking Serverless Computing Platforms

This hands-on session will guide you through deploying, testing, and benchmarking serverless functions using SeBS on both local Docker and OpenWhisk platforms.
Alternatively, you can deploy all functions to the cloud.
For details on setting up your account, please check SeB'S documentation.

---

## System Requirements

**OS**: Linux (Ubuntu 20.04+ recommended). We have not tested SeBS extensively on WSL and macOS, but we have reports from users that it works.

**Software**:
  - Docker 20.10+
  - Python 3.7+
  - Git
  - jq (JSON processor)
  - curl

**Cloud Accounts** (optional):
  - AWS, Azure, or GCP account with permissions to create serverless functions (if deploying to cloud platforms)
  - When deploying to OpenWhisk, a [free DockerHub account](https://www.docker.com/products/personal/) is needed to publish function images. Private Docker registries are not supported on `kind`.

## Table of Contents

- [Part 0: Setup and Prerequisites](steps/0_setup.md)
- [Part 1: Storage & Local Deployment](steps/1_local_deployment.md)
- [Part 2: FaaS Platforms & Experiments](steps/2_faas_deployment.md)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

---

## Troubleshooting

### General Debugging Tips

1. **Check logs first:**
   - Local: `docker logs <container-id>`
   - OpenWhisk: `wsk activation logs <activation-id>`
   - Cloud platforms: check respective dashboards

2. **Start simple:**
   - Test with `110.dynamic-html` (no dependencies)
   - Use `test` input size (smallest, fastest)
   - Deploy locally before using FaaS system. 

3. **Verify each step:**
   - After each deployment, test with one invocation
   - Check output structure before proceeding
   - Use `jq` to validate JSON output

3. **Clean state:**
   - When running into consistency issues, clean cache: `rm -rf cache` or modify cache entries manually (everything is in JSON)
   - Restart deployments from scratch (particularly OpenWhisk)
   - Delete and recreate cluster

4. **Ask for help:**
   - Join our Slack: https://serverlessbenchmark.slack.com
   - Open an issue on GitHub : https://github.com/spcl/serverless-benchmarks/issues
     Please provide your configuration, full command and error output

### Docker Issues

**Problem:** `permission denied` when running Docker commands

**Solution:**
```bash
sudo usermod -aG docker $USER
# Logout and login again
docker ps  # Should work without sudo
```

---

**Problem:** Port conflicts (port 9000, 9011 already in use)

**Solution:**

Check that you do not already have SeBS or storage containers running from prior experiments:

```bash
docker ps
```

Alternatively, find process using the port:

```bash
sudo lsof -i :9000
```

---

### OpenWhisk Issues

**Problem:** Pods stuck in `Pending` or `ContainerCreating` state

**Solution:**
Check pod details

```bash
kubectl describe pod <pod-name> -n openwhisk
```

You can restart the deployment

```bash
kind delete cluster --name openwhisk
cd tools && python3 openwhisk_preparation.py
```

### SeBS Issues

**Problem:** `ModuleNotFoundError` or import errors

**Solution:**
Ensure the virtual environment is activated

```bash
source python-venv/bin/activate
```

Then, verify the activation

```bash
which python
```

This should show: `/path/to/serverless-benchmarks/python-venv/bin/python`

---

**Problem:** Function returns empty or error result

**Solution:**

Check function execution logs. The actual solution depends on the platform.

Example for OpenWhisk:

```bash
wsk activation list
wsk activation logs <activation-id>
```

Alternatively, test locally first. This provides the quickest setup for debugging.

```bash
./sebs.py local start <benchmark> test output.json --config configs/local.json
```

---

### Storage Issues

**Problem:** MinIO unreachable from the function, particularly deployed on OpenWhisk (connection refused).

**Solution:**
Verify that the storage configuration uses the external address of your system.

This command should provide the address of your system.

```bash
hostname -I | awk '{print $1}'
```

Then, update the storage config with the correct address.

```bash
jq --arg ip "$(hostname -I | awk '{print $1}')" \
   '.object.minio.address = ($ip + ":9011")' \
   storage.json > fixed_storage.json
```

---

## Quick Reference

### SeBS Commands

```bash
# Deploy and invoke
./sebs.py benchmark invoke <benchmark> <input-size> \
    --config <config.json> \
    --deployment <local|openwhisk> \
    --verbose

# Local deployment
./sebs.py local start <benchmark> <input-size> <output.json> \
    --config <config.json> \
    --deployments 1

./sebs.py local stop <output.json>

# Storage management
./sebs.py storage start object <config.json> --output-json <output.json>
./sebs.py storage stop object <output.json>

# Experiments
./sebs.py experiment invoke perf-cost \
    --config <config.json> \
    --deployment <local|openwhisk> \
    --output-dir <results/>
```

### OpenWhisk Commands

```bash
# List actions
wsk action list

# Invoke action
wsk action invoke <action-name> --param key value --result

# Get action details
wsk action get <action-name> --summary

# View logs
wsk activation list
wsk activation logs <activation-id>

# Delete action
wsk action delete <action-name>
```

### kubectl Commands

```bash
# Get pods
kubectl get pods -n openwhisk

# Describe pod
kubectl describe pod <pod-name> -n openwhisk

# View logs
kubectl logs <pod-name> -n openwhisk

# Get nodes
kubectl get nodes
```

### kind Commands

Create cluster:

```bash
kind create cluster --name openwhisk --config kind-cluster.yaml

# Delete cluster
kind delete cluster --name openwhisk

# Get clusters
kind get clusters
```

